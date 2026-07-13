# 多階段：先用 Node build 前端，再放進 Python runtime，由 FastAPI 一併提供。
# 建置（context = repo 根）：
#   docker build -f deploy/Dockerfile -t hs-story .
# 執行：
#   docker run -p 8000:8000 -e ADMIN_PASSWORD=... -e SECRET_KEY=... \
#     -e ANTHROPIC_API_KEY=... -e PUBLIC_BASE_URL=https://your-domain \
#     -v hs_data:/data hs-story

# ---- 1. build 前端 ----
FROM node:20-alpine AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ---- 2. backend runtime ----
FROM python:3.11-slim AS app
WORKDIR /app

# Litestream：把 SQLite 持續複製到物件儲存（B2），容器啟動時還原最新 DB。
# 免費平台（Render）檔案系統是 ephemeral，資料持久化靠這個 sidecar。
COPY --from=litestream/litestream:0.3.13 /usr/local/bin/litestream /usr/local/bin/litestream

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=web /web/dist ./web/dist
COPY deploy/litestream.yml /etc/litestream.yml
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# SQLite 本地路徑（非持久；持久化來源是 B2，開機由 entrypoint 還原）
ENV HS_DB_PATH=/data/hs.db
# 平台會注入自己的 $PORT；entrypoint 用 ${PORT:-8000} 展開，本地無 PORT 時退回 8000。
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
