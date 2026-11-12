#!/usr/bin/env bash
# 一键关闭生产容器（./data 数据与镜像保留，./start.sh 可随时再启）
# 用法：./stop.sh
set -euo pipefail
cd "$(dirname "$0")"

docker compose down
echo "✓ 已停止。数据仍保留在 ./data，重新启动运行 ./start.sh"
