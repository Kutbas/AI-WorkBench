"""图像生成：多提示词并发 job（移植 generate_batch.py 的并发思路，信号量 4）。"""

from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .. import settings
from ..services import cos_uploader, dmxapi_image
from ..settings import DATA_DIR
from ..taskmanager import TaskManager

router = APIRouter(prefix="/api/imagegen", tags=["imagegen"])

IMAGES_DIR = DATA_DIR / "images"
MAX_CONCURRENCY = 4


class TaskIn(BaseModel):
    name: str = ""
    prompt: str


class JobIn(BaseModel):
    tasks: list[TaskIn]
    params: dict = {}


def _tm(request: Request) -> TaskManager:
    return request.app.state.tm  # type: ignore[no-any-return]


async def _run_job(tm: TaskManager, job_id: str, names: list[str], prompts: list[str], params: dict) -> None:
    cfg = settings.get_config()
    base_url, api_key = cfg["dmxapi"]["base_url"], cfg["dmxapi"]["api_key"]
    cos_cfg = cfg["cos"]
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def run_one(idx: int, name: str, prompt: str) -> None:
        async with sem:
            tm.start_task(job_id, idx)
            try:
                images = await dmxapi_image.generate_images(base_url, api_key, prompt, params)
            except Exception as e:
                tm.finish_task(job_id, idx, ok=False, error=str(e))
                return
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe = TaskManager.safe_name(name, fallback=f"task{idx + 1}")
            results = []
            for i, img in enumerate(images, start=1):
                filename = f"{ts}_{safe}_{i}.png"
                IMAGES_DIR.mkdir(parents=True, exist_ok=True)
                (IMAGES_DIR / filename).write_bytes(img)
                rec: dict = {"filename": filename}
                try:  # COS 上传失败不影响本地结果展示，前端可手动重传
                    prefix = cos_cfg.get("prefix", "").rstrip("/")
                    key = f"{prefix}/{filename}" if prefix else filename
                    rec["cos_key"] = key
                    rec["cos_url"] = await cos_uploader.upload(cos_cfg, key, img)
                except Exception as e:
                    rec["upload_error"] = str(e)
                results.append(rec)
            tm.finish_task(job_id, idx, ok=True, images=results)

    await asyncio.gather(*(run_one(i, n, p) for i, (n, p) in enumerate(zip(names, prompts))))


@router.post("/jobs")
async def create_job(body: JobIn, request: Request) -> dict:
    prompts = [t.prompt.strip() for t in body.tasks]
    if not prompts or not all(prompts):
        raise HTTPException(status_code=400, detail="每个提示词不能为空")
    cfg = settings.get_config()
    # 前端显式传参优先，未传的字段落回设置页保存的默认值
    params = {**cfg["imagegen"], **{k: v for k, v in body.params.items() if v not in (None, "")}}
    names = [t.name.strip() or f"task{i + 1}" for i, t in enumerate(body.tasks)]
    tm = _tm(request)
    job = tm.create("imagegen", params, names)
    asyncio.create_task(_run_job(tm, job["id"], names, prompts, params))
    return {"job_id": job["id"]}


@router.get("/jobs")
async def list_jobs(request: Request, limit: int = 20) -> list[dict]:
    return _tm(request).list("imagegen", limit)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> dict:
    job = _tm(request).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@router.post("/images/{filename}/reupload")
async def reupload(filename: str) -> dict:
    path = (IMAGES_DIR / filename).resolve()
    if not str(path).startswith(str(IMAGES_DIR.resolve())) or not path.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")
    cfg = settings.get_config()["cos"]
    prefix = cfg.get("prefix", "").rstrip("/")
    key = f"{prefix}/{filename}" if prefix else filename
    url = await cos_uploader.upload(cfg, key, path.read_bytes())
    return {"ok": True, "cos_url": url, "cos_key": key}
