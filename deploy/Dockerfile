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
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=web /web/dist ./web/dist

# SQLite 放在持久卷 /data（雲端平台掛 volume 到此路徑，避免重佈遺失資料）
ENV HS_DB_PATH=/data/hs.db
EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
