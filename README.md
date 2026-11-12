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

## 服务器部署（Ubuntu + Docker）

```bash
git clone https://github.com/Kutbas/AI-WorkBench.git
cd AI-WorkBench
cp .env.example .env
# 编辑 .env：APP_ENV=production、ACCESS_TOKEN=强口令、各密钥
docker compose up -d --build
# 访问 http://<服务器IP>:8720
```

数据持久化在宿主 `./data`（配置、图片、解析结果、任务记录）。反向代理（1Panel/nginx）时保留 `/api` 前缀即可。

> 安全提醒：COS 密钥与 API Key 只放在服务器的 `.env`（不入库）。若怀疑泄露，请到腾讯云控制台轮换 SecretKey。
