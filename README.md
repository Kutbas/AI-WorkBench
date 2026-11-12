# AI-WorkBench

个人 AI 工具工作台：把常用脚本整合成浏览器可访问的页面，每个功能一个页面，可持续扩展。

## 功能

| 页面 | 功能 | 来源脚本 |
|------|------|----------|
| 图像生成 | 多提示词并发生图（DMXAPI），自动上传腾讯 COS 图床 | `ImageGenerate/generate_batch.py` |
| 文档解析 | SoMark 解析 PDF/图片 → Markdown/纯文本/原始 JSON，批量合并 | `SoMark/somark_client.py`、`batch_parse.py` |
| 文本清洗 | 按分隔符分段、去多余空白、双换行拼接 | `LearnLangChain/script.py` |
| 设置 | DMXAPI / COS / 生成参数 / 访问口令，运行时可改 | — |

## 技术栈

- 后端：FastAPI（Python 3.12，uv 管理依赖），httpx，cos-python-sdk-v5
- 前端：Vue 3 + TypeScript + Vite + Element Plus
- 部署：多阶段 Docker（node 构建前端 → python 运行后端并托管静态产物），docker-compose 单容器

## 环境隔离

- **开发**（本机）：`uv run uvicorn app.main:app --reload --port 8000` + `npm run dev`（Vite 5173，代理 `/api`）。未设 `ACCESS_TOKEN` 时免登录
- **生产**（服务器 Docker）：`APP_ENV=production`，`ACCESS_TOKEN` 必填（未设启动即失败）；`/docs` 关闭
- 配置与数据（`data/config.json`、生成的图片、解析结果）只存在于各自机器，不入库、不进镜像

## 快速开始（本地开发）

```bash
cp .env.example .env   # 填入 DMXAPI_API_KEY / COS 密钥（可选，设置页也能改）

# 后端（端口 8000）
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000

# 前端（端口 5173，代理 /api → 8000）
cd frontend && npm install && npm run dev
```

## 一键脚本

**本机（开发环境）**：

```bash
./start.sh   # 一键开启生产容器：构建（国内源加速）→ 启动 → 健康检查 → http://localhost:8720
./stop.sh    # 一键关闭（./data 数据与镜像保留，随时可再启）
```

**服务器（Ubuntu）**：

```bash
git clone https://github.com/Kutbas/AI-WorkBench.git && cd AI-WorkBench
./deploy.sh            # 一键部署：首装交互式生成 .env（口令必填可随机、密钥可跳过）；更新时自动 git pull + 重建
./deploy.sh status     # 查看容器与服务状态
./deploy.sh logs       # 跟踪日志
./deploy.sh restart    # 重启（改 .env 后生效用）
./deploy.sh down       # 停止（数据保留）
```

> 脚本默认使用国内镜像源加速构建（npmmirror / aliyun pypi），可用环境变量 `NPM_REGISTRY` / `PIP_INDEX_URL` / `PORT` 覆盖。

## 手动部署（等价于 deploy.sh）

```bash
git clone https://github.com/Kutbas/AI-WorkBench.git
cd AI-WorkBench
cp .env.example .env
# 编辑 .env：APP_ENV=production、ACCESS_TOKEN=强口令、各密钥
docker compose up -d --build
# 访问 http://<服务器IP>:8720
```

国内网络构建加速（npm/pypi 走镜像源）：

```bash
docker compose build \
  --build-arg NPM_REGISTRY=https://registry.npmmirror.com \
  --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
```

依赖说明：容器内用 `backend/requirements.txt`（由 `uv.lock` 导出、带 hash 锁定）经 pip 安装。
**改动后端依赖后需重新导出**：`cd backend && uv export --frozen --no-dev --no-emit-project -o requirements.txt`

数据持久化在宿主 `./data`（配置、图片、解析结果、任务记录）。反向代理（1Panel/nginx）时保留 `/api` 前缀即可。

> 安全提醒：COS 密钥与 API Key 只放在服务器的 `.env`（不入库）。若怀疑泄露，请到腾讯云控制台轮换 SecretKey。
