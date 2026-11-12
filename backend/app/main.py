"""AI-WorkBench 后端入口。

环境分流（APP_ENV=development|production）：
- development：CORS 放行 Vite 5173；/docs 开放；未设 ACCESS_TOKEN 时免登录
- production：/docs 关闭；未设 ACCESS_TOKEN 启动即失败（强制门禁）
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")  # 本地开发读项目根 .env；生产容器由 compose env_file 注入

from . import settings
from .routers import auth, imagegen, somark
from .routers import settings as settings_router
from .taskmanager import TaskManager

APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
PRODUCTION = APP_ENV == "production"

# 无需登录的 API（探测/登录本身）
_EXEMPT = {"/api/auth/login", "/api/auth/status"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.load_config()
    if PRODUCTION and not settings.get_config()["access_token"]:
        raise RuntimeError("APP_ENV=production 但未设置访问口令：请在 .env 配置 ACCESS_TOKEN 后重启")
    app.state.tm = TaskManager(settings.DATA_DIR / "jobs")
    app.state.tm.load_all()
    print(f"[main] APP_ENV={APP_ENV} | data dir: {settings.DATA_DIR}")
    yield


app = FastAPI(
    title="AI-WorkBench",
    lifespan=lifespan,
    docs_url=None if PRODUCTION else "/docs",
    redoc_url=None if PRODUCTION else "/redoc",
    openapi_url=None if PRODUCTION else "/openapi.json",
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """口令门禁：X-Auth-Token 头或 aiwb_token cookie（供 <img> 等同源请求）任一匹配即放行。"""
    token = settings.get_config()["access_token"]
    path = request.url.path
    if token and path.startswith("/api/") and path not in _EXEMPT:
        provided = request.headers.get("x-auth-token") or request.cookies.get("aiwb_token")
        if provided != token:
            return JSONResponse({"detail": "未授权，请先登录"}, status_code=401)
    return await call_next(request)


# CORS 需位于 auth 外层（后注册的先执行），401 响应才带 CORS 头、开发前端才能读到状态码
if not PRODUCTION:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth.router)
app.include_router(settings_router.router)
app.include_router(imagegen.router)
app.include_router(somark.router)

# 生成图片的预览服务（同源 <img> 自动带 cookie 过门禁）
IMAGES_DIR = settings.DATA_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/files/images", StaticFiles(directory=IMAGES_DIR), name="images")


# 前端 SPA：dist 存在则托管（生产/本地构建预览）；开发模式走 Vite 5173
# 查找顺序：DIST_DIR 环境变量（容器内用）→ 项目内 frontend/dist → 项目根 static/
_DIST_CANDIDATES = [
    Path(os.environ["DIST_DIR"]) if os.environ.get("DIST_DIR") else None,
    PROJECT_ROOT / "frontend" / "dist",
    PROJECT_ROOT / "static",
]
DIST = next((d for d in _DIST_CANDIDATES if d and d.is_dir()), None)
if DIST is not None:
    dist_root = DIST.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> Response:
        if full_path:
            f = (DIST / full_path).resolve()
            if str(f).startswith(str(dist_root)) and f.is_file():
                return FileResponse(f)
        return FileResponse(DIST / "index.html")
