"""设置页：配置读取/保存、COS 连通性测试。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import settings
from ..services import cos_uploader

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings() -> dict:
    return settings.get_config()


@router.put("")
async def put_settings(updates: dict) -> dict:
    return settings.save_config(updates)


class TestCosIn(BaseModel):
    # 允许用表单里未保存的值直接测（体验更好）；为空则用当前已保存配置
    cos: dict | None = None


@router.post("/test-cos")
async def test_cos(body: TestCosIn) -> dict:
    cfg = settings.get_config()
    merged = {**cfg["cos"], **{k: v for k, v in (body.cos or {}).items() if v}} if body.cos else cfg["cos"]
    try:
        msg = await cos_uploader.test_connection(merged)
    except cos_uploader.CosUploadError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "message": msg}
