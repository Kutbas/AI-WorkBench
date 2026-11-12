"""SoMark 文档解析（移植自 SoMark/somark_client.py，requests → httpx 异步）。

要点（与原脚本一致）：
- POST https://www.dmxapi.cn/v1/responses，Authorization 头直接放 API Key（无 Bearer）
- payload: {"model": "somark", "input": "json", "file": "<base64>"}
- 4xx（除 429）不重试；超时/连接错误/5xx/429 重试，等待 5*attempt 秒
- 后处理：strip_references（按 bbox 切掉 References 起至文末）、extract_text、extract_markdown
"""

from __future__ import annotations

import asyncio
import base64
import copy
import json

import httpx

SUPPORTED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}

REQUEST_TIMEOUT = httpx.Timeout(300.0, connect=15.0)


class SoMarkError(RuntimeError):
    pass


async def parse_document(
    base_url: str,
    api_key: str,
    file_bytes: bytes,
    retries: int = 2,
) -> dict:
    """调用 SoMark 解析文档字节，返回完整响应 JSON（data.result.outputs.json.pages 结构）。

    Raises:
        SoMarkError: 接口返回非 200 / 响应缺少结果字段 / 重试耗尽
    """
    payload = {
        "model": "somark",
        "input": "json",
        "file": base64.b64encode(file_bytes).decode("ascii"),
    }
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    url = f"{base_url.rstrip('/')}/v1/responses"

    last_err: Exception | None = None
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for attempt in range(1, retries + 2):
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # 校验到解析结果那一层，失败及早暴露
                    data["data"]["result"]["outputs"]["json"]["pages"]
                    return data
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    # 4xx 多为请求/key 问题，重试无益
                    raise SoMarkError(f"接口返回 {resp.status_code}: {resp.text[:500]}")
                last_err = SoMarkError(f"接口返回 {resp.status_code}: {resp.text[:500]}")
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_err = e
            except SoMarkError:
                raise
            if attempt <= retries:
                await asyncio.sleep(5 * attempt)
    raise SoMarkError(f"SoMark 请求失败（已重试 {retries} 次）: {last_err}")


# ---------- 以下后处理为纯函数，逻辑与原脚本逐字一致 ----------


def strip_references(doc: dict) -> dict:
    """去掉 References 起到文末的全部内容，返回新 doc（不动原对象）。

    定位第一个内容为 "References" 的 title 块：
    - 所在页仅保留完全位于其上方的块（块 bbox 底边 <= 标题 bbox 顶边）
    - 之后的所有页整体删除
    未找到时原样返回（深拷贝）。
    """
    new = copy.deepcopy(doc)
    pages = new["data"]["result"]["outputs"]["json"]["pages"]
    for pi, page in enumerate(pages):
        for b in page.get("blocks", []):
            if b.get("type") == "title" and b.get("content", "").strip().lower() == "references":
                ref_top = b["bbox"][1]
                page["blocks"] = [x for x in page["blocks"] if x is not b and x["bbox"][3] <= ref_top]
                del pages[pi + 1 :]
                return new
    return new


def iter_blocks(doc: dict):
    """按 (页码, 块) 迭代解析结果，页码转成从 1 开始（接口原始字段 page_num 从 0 起）。"""
    pages = doc["data"]["result"]["outputs"]["json"]["pages"]
    for page in pages:
        yield page.get("page_num", 0) + 1, page.get("blocks", [])


def extract_text(doc: dict, figure_urls: bool = True) -> str:
    """提取纯文本，figure 块以占位符（附图床链接与语义描述）标注。figure_urls=False 去掉链接只留描述。"""
    lines: list[str] = []
    for page_no, blocks in iter_blocks(doc):
        lines.append(f"===== Page {page_no} =====")
        for b in blocks:
            if b.get("type") == "figure":
                if figure_urls:
                    lines.append(f"[图片 {b.get('img_url', '')} 描述: {b.get('content', '').strip()}]")
                else:
                    lines.append(f"[图] {b.get('content', '').strip()}")
            else:
                c = b.get("content", "")
                if c:
                    lines.append(c)
        lines.append("")
    return "\n".join(lines)


def extract_markdown(doc: dict, skip_header: bool = True, page_comments: bool = True, figure_urls: bool = True) -> str:
    """转成简易 Markdown。

    - title → 一级标题；figure → ![语义描述](图床链接)（SoMark 会为图片生成中文描述）
    - 表格 content 为 HTML，原样嵌入；header（页眉）默认作为噪声跳过
    - page_comments=False 去掉页码注释；figure_urls=False 时 figure 只输出"[图] 描述"不带链接
    """
    parts: list[str] = []
    for page_no, blocks in iter_blocks(doc):
        if page_comments:
            parts.append(f"\n<!-- page {page_no} -->\n")
        for b in blocks:
            t = b.get("type", "")
            c = (b.get("content") or "").strip()
            if t == "header" and skip_header:
                continue
            if t == "title" and c:
                parts.append(f"# {c}\n")
            elif t == "figure":
                if figure_urls and b.get("img_url"):
                    parts.append(f"![{c or 'figure'}]({b['img_url']})\n")
                elif c:
                    parts.append(f"[图] {c}\n")
            elif c:
                parts.append(f"{c}\n")
    return "\n".join(parts).strip() + "\n"


def block_stats(doc: dict) -> dict[str, int]:
    """块类型统计。"""
    stats: dict[str, int] = {}
    for _, blocks in iter_blocks(doc):
        for b in blocks:
            stats[b.get("type", "?")] = stats.get(b.get("type", "?"), 0) + 1
    return stats


def dump_json(doc: dict) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=2)
