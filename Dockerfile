# ---------- 阶段 1：构建前端 ----------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- 阶段 2：后端运行时 ----------
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
# 先只拷依赖清单，充分利用层缓存
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app
COPY --from=frontend /build/dist ./static

# 生产配置（口令等经 compose env_file 注入）
ENV APP_ENV=production \
    DATA_DIR=/app/data \
    DIST_DIR=/app/static

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
