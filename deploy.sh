#!/usr/bin/env bash
# Ubuntu 服务器一键部署/更新（首装交互式生成 .env，更新则 git pull + 重建）
# 用法：./deploy.sh [up|down|restart|logs|status]   （默认 up）
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8720}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmmirror.com}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"
CMD="${1:-up}"

# sed -i 的 GNU/BSD 兼容（服务器 GNU，开发机 BSD）
sed_inplace() {
  if sed --version 2>/dev/null | grep -q GNU; then sed -i "$@"; else sed -i '' "$@"; fi
}

need_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "✗ 未安装 docker，请先安装：curl -fsSL https://get.docker.com | sh"
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "✗ docker compose 插件不可用（需 Docker 20.10+）"
    exit 1
  fi
}

wait_healthy() {
  echo "==> 等待服务就绪"
  for _ in $(seq 1 30); do
    if curl -sf "http://localhost:$PORT/api/auth/status" >/dev/null 2>&1; then
      local ip
      ip=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
      echo ""
      echo "✓ AI-WorkBench 已就绪"
      if [ -n "$ip" ]; then
        echo "  访问地址: http://${ip}:${PORT} （本机则 http://localhost:${PORT}）"
      else
        echo "  访问地址: http://localhost:${PORT}"
      fi
      echo "  数据持久化在 ./data；日志: ./deploy.sh logs；停止: ./deploy.sh down"
      return 0
    fi
    printf "."
    sleep 2
  done
  echo ""
  echo "✗ 服务未能就绪，查看日志：./deploy.sh logs"
  return 1
}

first_setup() {
  echo "==> 首次部署：生成 .env（回车可跳过可选项，之后在工作台「设置」页填写）"
  cp .env.example .env

  local token=""
  read -r -p "访问口令 ACCESS_TOKEN（回车=随机生成）: " token
  if [ -z "$token" ]; then
    token=$(head -c 16 /dev/urandom | md5sum 2>/dev/null | head -c 16 || openssl rand -hex 8 2>/dev/null)
    echo "  已生成随机口令: ${token}（请务必保存）"
  fi
  sed_inplace "s|^ACCESS_TOKEN=.*|ACCESS_TOKEN=$token|" .env

  local v=""
  read -r -p "DMXAPI API Key（图像生成/文档解析共用，回车跳过）: " v
  [ -n "$v" ] && sed_inplace "s|^DMXAPI_API_KEY=.*|DMXAPI_API_KEY=$v|" .env
  read -r -p "COS SecretId（回车跳过）: " v
  [ -n "$v" ] && sed_inplace "s|^COS_SECRET_ID=.*|COS_SECRET_ID=$v|" .env
  read -r -p "COS SecretKey（回车跳过）: " v
  [ -n "$v" ] && sed_inplace "s|^COS_SECRET_KEY=.*|COS_SECRET_KEY=$v|" .env
  read -r -p "COS Bucket（如 graphbed-1331926955，回车跳过）: " v
  [ -n "$v" ] && sed_inplace "s|^COS_BUCKET=.*|COS_BUCKET=$v|" .env
  read -r -p "COS 存储区域（默认 ap-shanghai）: " v
  [ -n "$v" ] && sed_inplace "s|^COS_REGION=.*|COS_REGION=$v|" .env
  read -r -p "COS 存储路径前缀（默认 GraphBed/）: " v
  [ -n "$v" ] && sed_inplace "s|^COS_PREFIX=.*|COS_PREFIX=$v|" .env
}

case "$CMD" in
  up)
    need_docker
    [ -f .env ] || first_setup

    # 更新部署：git 仓库则先拉代码（本地有改动时跳过并提示）
    if git rev-parse --git-dir >/dev/null 2>&1; then
      if git pull --ff-only >/dev/null 2>&1; then
        echo "==> 已拉取最新代码: $(git log --oneline -1)"
      else
        echo "==> git pull 跳过（无远程更新或本地有改动），继续用当前代码部署"
      fi
    fi

    echo "==> 构建镜像（npm: ${NPM_REGISTRY} | pypi: ${PIP_INDEX_URL}）"
    docker compose build \
      --build-arg NPM_REGISTRY="$NPM_REGISTRY" \
      --build-arg PIP_INDEX_URL="$PIP_INDEX_URL"
    docker compose up -d
    wait_healthy
    ;;
  down)
    need_docker
    docker compose down
    echo "✓ 已停止（./data 数据保留）"
    ;;
  restart)
    need_docker
    docker compose restart
    wait_healthy
    ;;
  logs)
    need_docker
    docker compose logs -f --tail 100
    ;;
  status)
    need_docker
    docker compose ps
    curl -s "http://localhost:$PORT/api/auth/status" && echo
    ;;
  *)
    echo "用法: $0 [up|down|restart|logs|status]"
    exit 1
    ;;
esac
