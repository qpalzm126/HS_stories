#!/bin/sh
# 容器進入點：先從 B2 還原最新 SQLite（若本地沒有且遠端有備份），
# 再用 litestream 監督 uvicorn——app 執行期間持續把 WAL 複製到 B2，
# app 結束時 litestream 會一併收尾（含最後一次同步）。
set -e

mkdir -p "$(dirname "$HS_DB_PATH")"

# 首次部署時 B2 尚無備份 → -if-replica-exists 讓它安靜略過，app 會建新 DB。
litestream restore -if-db-not-exists -if-replica-exists "$HS_DB_PATH"

exec litestream replicate -exec "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}"
