"""SoMark 文档解析：多文件 job，按提交顺序串行解析（防限流，同原批量脚本），完成后合并 all.md。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from .. import settings
from ..services import somark as somark_svc
from ..settings import DATA_DIR
from ..taskmanager import TaskManager

router = APIRouter(prefix="/api/somark", tags=["somark"])

SOMARK_DIR = DATA_DIR / "somark"


def _tm(request: Request) -> TaskManager:
    return request.app.state.tm  # type: ignore[no-any-return]


def _job_dir(job_id: str):
    d = (SOMARK_DIR / job_id).resolve()
    if not str(d).startswith(str(SOMARK_DIR.resolve())):
        raise HTTPException(status_code=400, detail="非法任务 id")
    return d


async def _run_job(tm: TaskManager, job_id: str, uploads: list[Path], opts: dict) -> None:
    cfg = settings.get_config()
    base_url, api_key = cfg["dmxapi"]["base_url"], cfg["dmxapi"]["api_key"]
    out_dir = _job_dir(job_id)
    plain = opts.get("plain", False)
    strip_refs = opts.get("strip_refs", False)

    for idx, src in enumerate(uploads):  # 串行：与原批量脚本一致，避免触发限流
        tm.start_task(job_id, idx)
        try:
            doc = await somark_svc.parse_document(base_url, api_key, src.read_bytes())
            doc_out = somark_svc.strip_references(doc) if strip_refs else doc
            stem = src.stem
            (out_dir / f"{stem}.raw.json").write_text(somark_svc.dump_json(doc), encoding="utf-8")
            (out_dir / f"{stem}.txt").write_text(
                somark_svc.extract_text(doc_out, figure_urls=not plain), encoding="utf-8"
            )
            (out_dir / f"{stem}.md").write_text(
                somark_svc.extract_markdown(doc_out, page_comments=not plain, figure_urls=not plain),
                encoding="utf-8",
            )
            tm.finish_task(job_id, idx, ok=True, stem=stem, stats=somark_svc.block_stats(doc_out))
        except Exception as e:
            tm.finish_task(job_id, idx, ok=False, error=str(e))

    # 按提交顺序合并全部成功结果（纯文字阅读版，同 batch_parse.py）
    job = tm.get(job_id)
    ok = [(i, t) for i, t in enumerate(job["tasks"]) if t["status"] == "done"] if job else []
    if ok:
        merged = [f"# SoMark 批量识别汇总（{len(ok)}/{len(uploads)} 个文件）\n"]
        for i, t in ok:
            doc = json.loads((out_dir / f"{t['stem']}.raw.json").read_text(encoding="utf-8"))
            doc_out = somark_svc.strip_references(doc) if strip_refs else doc
            merged.append(f"\n---\n\n<!-- {t['stem']} -->\n")
            merged.append(somark_svc.extract_markdown(doc_out, page_comments=False, figure_urls=False))
        (out_dir / "all.md").write_text("".join(merged), encoding="utf-8")


@router.post("/jobs")
async def create_job(
    request: Request,
    files: list[UploadFile] = File(...),
    strip_refs: bool = Form(False),
    plain: bool = Form(False),
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="未选择文件")
    stems: list[str] = []
    for f in files:
        ext = "." + f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in somark_svc.SUPPORTED_EXTS:
            raise HTTPException(status_code=400, detail=f"不支持的格式 {f.filename}（支持 pdf/图片）")
        stems.append(TaskManager.safe_name(f.filename.rsplit(".", 1)[0], fallback="file"))

    tm = _tm(request)
    # 前缀序号保证按提交顺序展示与合并、避免同名撞文件
    task_names = [f"{i:02d}_{s}" for i, s in enumerate(stems)]
    job = tm.create("somark", {"strip_refs": strip_refs, "plain": plain, "files": [f.filename for f in files]}, task_names)
    out_dir = _job_dir(job["id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    uploads = []
    for f, name in zip(files, task_names):  # 原文件落盘，重传/复解析不必重新上传
        p = out_dir / f"{name}{Path(f.filename).suffix.lower()}"
        p.write_bytes(await f.read())
        uploads.append(p)
    asyncio.create_task(_run_job(tm, job["id"], uploads, {"strip_refs": strip_refs, "plain": plain}))
    return {"job_id": job["id"]}


@router.get("/jobs")
async def list_jobs(request: Request, limit: int = 20) -> list[dict]:
    return _tm(request).list("somark", limit)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> dict:
    job = _tm(request).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


_EXT = {"md": ".md", "txt": ".txt", "json": ".raw.json"}


def _result_path(job_id: str, stem: str, fmt: str) -> Path:
    if fmt not in _EXT:
        raise HTTPException(status_code=400, detail="fmt 仅支持 md/txt/json")
    job_dir = _job_dir(job_id)
    # stem 必须来自任务记录，防路径穿越
    path = (job_dir / f"{stem}{_EXT[fmt]}").resolve()
    if not str(path).startswith(str(job_dir)) or not path.is_file():
        raise HTTPException(status_code=404, detail="结果文件不存在")
    return path


@router.get("/jobs/{job_id}/files/{stem}/{fmt}")
async def get_file(job_id: str, stem: str, fmt: str) -> FileResponse:
    path = _result_path(job_id, stem, fmt)
    return FileResponse(path, filename=path.name, media_type="text/plain; charset=utf-8")


@router.get("/jobs/{job_id}/merged")
async def get_merged(job_id: str) -> FileResponse:
    path = _job_dir(job_id) / "all.md"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="合并文件不存在（可能全部失败或仅单文件）")
    return FileResponse(path, filename="all.md", media_type="text/plain; charset=utf-8")
