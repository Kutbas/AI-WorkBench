# ---------- 阶段 1：构建前端 ----------
# NPM_REGISTRY 构建参数：网络受限时可传国内镜像源
#   docker build --build-arg NPM_REGISTRY=https://registry.npmmirror.com
ARG NPM_REGISTRY=https://registry.npmjs.org
FROM node:20-alpine AS frontend
ARG NPM_REGISTRY
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --registry=$NPM_REGISTRY
COPY frontend/ ./
RUN npm run build

# ---------- 阶段 2：后端运行时 ----------
# 依赖版本由 backend/requirements.txt 锁定（由 uv.lock 导出，改依赖后需重新导出）：
#   cd backend && uv export --frozen --no-dev --no-emit-project -o requirements.txt
# PIP_INDEX_URL 构建参数：网络受限时可传国内镜像源
#   docker build --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_INDEX_URL=https://pypi.org/simple
FROM python:3.12-slim
ARG PIP_INDEX_URL
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
WORKDIR /app

# 先只拷依赖清单，充分利用层缓存（含 hash 校验，与 uv.lock 完全一致）
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /build/dist ./static

# 生产配置（口令等经 compose env_file 注入）
ENV APP_ENV=production \
    DATA_DIR=/app/data \
    DIST_DIR=/app/static

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
