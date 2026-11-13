#!/usr/bin/env bash
# 开发机一键开启生产容器：构建（国内镜像源加速）→ 启动 → 健康检查
# 用法：./start.sh
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8720}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "✗ 未找到 .env，已从 .env.example 生成一份。"
  echo "  请编辑 .env 填写 ACCESS_TOKEN（生产模式必填）等配置后，重新运行 ./start.sh"
  exit 1
fi

# 生产模式强制口令：首次启动（data/config.json 尚不存在）时 .env 必须已设口令
if [ ! -f data/config.json ] && ! grep -qE '^ACCESS_TOKEN=..+' .env; then
  echo "✗ 生产模式要求访问口令：请在 .env 中设置 ACCESS_TOKEN 后重试"
  exit 1
fi

# Docker daemon 前置检查：macOS 自动拉起 Docker Desktop 并等待就绪
# 探测加 5s 超时：Docker Desktop 半就绪时 docker CLI 可能无限挂死（macOS 无 timeout 命令，用 perl alarm）
docker_ready() {
  perl -e 'alarm 5; exec @ARGV' docker info >/dev/null 2>&1
}

ensure_docker_daemon() {
  if docker_ready; then
    return 0
  fi
  if [ "$(uname -s)" = "Darwin" ] && [ -d /Applications/Docker.app ]; then
    echo "==> Docker Desktop 未运行，正在启动…"
    open -a Docker || true
    for _ in $(seq 1 60); do
      if docker_ready; then
        echo "==> Docker daemon 已就绪"
        return 0
      fi
      printf "."
      sleep 2
    done
    echo ""
    echo "✗ 等待 Docker daemon 超时（120s），请手动打开 Docker Desktop 后重试"
    return 1
  fi
  echo "✗ Docker daemon 未运行：Linux 请执行 sudo systemctl start docker"
  return 1
}
ensure_docker_daemon

echo "==> 构建镜像（npm: ${NPM_REGISTRY} | pypi: ${PIP_INDEX_URL}）"
docker compose build \
  --build-arg NPM_REGISTRY="$NPM_REGISTRY" \
  --build-arg PIP_INDEX_URL="$PIP_INDEX_URL"

echo "==> 启动容器"
docker compose up -d

echo "==> 等待服务就绪"
for i in $(seq 1 30); do
  if curl -sf "http://localhost:$PORT/api/auth/status" >/dev/null 2>&1; then
    echo ""
    echo "✓ AI-WorkBench 已启动: http://localhost:$PORT"
    echo "  口令即 .env 中的 ACCESS_TOKEN；数据持久化在 ./data（./stop.sh 关闭）"
    exit 0
  fi
  printf "."
  sleep 2
done
echo ""
echo "✗ 服务未能就绪，查看日志：docker compose logs --tail 50"
exit 1
