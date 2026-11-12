"""认证：口令登录换取 token（头部 X-Auth-Token + cookie 双通道）。"""

from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .. import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "aiwb_token"
COOKIE_MAX_AGE = 30 * 24 * 3600


class LoginIn(BaseModel):
    password: str


@router.get("/status")
async def status() -> dict:
    """前端启动时探测：是否需要登录、运行模式。"""
    return {
        "need_auth": bool(settings.get_config()["access_token"]),
    }


@router.post("/login")
async def login(body: LoginIn, response: Response) -> dict:
    token = settings.get_config()["access_token"]
    if not token:
        return {"ok": True, "token": "", "message": "未启用口令，无需登录"}
    if body.password != token:
        return JSONResponse({"detail": "口令错误"}, status_code=401)
    # cookie 供 <img> 等无法带自定义头的同源请求使用
    response.set_cookie(COOKIE_NAME, token, max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax")
    return {"ok": True, "token": token}
