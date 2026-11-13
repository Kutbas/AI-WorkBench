#!/usr/bin/env bash
# 一键关闭生产容器（./data 数据与镜像保留，./start.sh 可随时再启）
# 用法：./stop.sh
set -euo pipefail
cd "$(dirname "$0")"

# daemon 未运行 = 容器本就没开，无需停止
if ! docker info >/dev/null 2>&1; then
  echo "✓ 未检测到运行中的 Docker（容器本就未开启），无需停止"
  exit 0
fi

docker compose down
echo "✓ 已停止。数据仍保留在 ./data，重新启动运行 ./start.sh"
