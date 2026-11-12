"""DMXAPI 图像生成（移植自 ImageGenerate/generate_batch.py）。

核心逻辑保持一致：POST {base}/v1/images/generations（Bearer 认证），
响应 data[].b64_json 或 data[].url 取图；提示词原文直传，零追加。
"""

from __future__ import annotations

import base64

import httpx

# 原脚本实测：生成耗时可达数分钟，读超时必须放宽
TIMEOUT = httpx.Timeout(540.0, connect=15.0)


class ImageGenError(RuntimeError):
    pass


async def generate_images(base_url: str, api_key: str, prompt: str, params: dict) -> list[bytes]:
    """按一组参数生成图片，返回图片字节列表（len == n）。

    params: model / size / n / quality / output_format / moderation / background
    """
    payload = {
        "model": params.get("model") or "gpt-image-2.5-sunburst-ssvip",
        "prompt": prompt,
        "n": int(params.get("n") or 1),
        "size": params.get("size") or "2048x1152",
        "output_format": params.get("output_format") or "png",
        "quality": params.get("quality") or "high",
        "moderation": params.get("moderation") or "low",
        "background": params.get("background") or "auto",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/v1/images/generations",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        if resp.status_code != 200:
            raise ImageGenError(f"接口返回 {resp.status_code}: {resp.text[:500]}")
        try:
            data = resp.json()
        except ValueError as e:
            raise ImageGenError(f"非 JSON 响应: {resp.text[:300]}") from e

        if "data" not in data or not data["data"]:
            raise ImageGenError(f"响应缺少 data 字段: {str(data)[:300]}")

        images: list[bytes] = []
        for item in data["data"]:
            if item.get("b64_json"):
                images.append(base64.b64decode(item["b64_json"]))
            elif item.get("url"):
                r = await client.get(item["url"], timeout=120.0)
                r.raise_for_status()
                images.append(r.content)
        if not images:
            raise ImageGenError("响应 data 内无 b64_json/url 字段")
        return images
