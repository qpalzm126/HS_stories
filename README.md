# 聖靈故事（HS Story）

把 **LINE 聊天記錄裡的見證/分享**，經 Gemini 產草稿、人工確認後**發佈成文章**，提供：

- **公開網站**：列出全部聖靈故事、文章詳情頁。
- **公開 API**：給手機 App 與桌面 widget 取文章（最新／列表／單篇、關鍵字搜尋）。
- **後台**：匯入 LINE、搜尋挑訊息、產草稿、編修、發佈。

> 內容管線：LINE 記錄 →（後台篩選 + Gemini 產草稿）→ 你確認發佈 → 網站 + App/Widget 顯示。

## 現況（分階段）

- ✅ **Phase A**：backend + 公開網站（列表／搜尋／日曆／文章詳情）+ 後台。
- 🔶 **Phase B**：Flutter App + 原生 widget。Android 已可編譯／執行／側載（模擬器驗證）；
  iOS 的 Widget Extension 仍需在 Xcode 手動接線（見 `app/README.md`）。需安裝 Flutter SDK。
- ✅ **Phase C**：以 Docker 部署到 Render；SQLite 靠 Litestream 持續備份到 Backblaze B2
  （Render 免費方案無持久磁碟）。⚠️ 目前 push **不會**自動部署，需在 Render 手動觸發（見部署章節）。

## 架構

```
backend/   FastAPI + SQLite(FTS5 trigram) + Google Gemini SDK
  parser.py / importer.py   解析＆匯入 LINE 匯出檔（去重）
  db.py                     messages + FTS、articles CRUD/發佈
  summarizer.py             Gemini 把對話改寫成文章草稿
  auth.py                   後台密碼登入 → 簽章 token
  articles.py               slug / 對外輸出整形
  app.py                    公開 API + 後台 API + 提供前端
web/       Vite + React（React Router）
  公開：/（列表）、/article/:slug（詳情，widget deep-link 目標）
  後台：/admin（登入/管理）、/admin/ingest（從 LINE 產生）、/admin/edit/:id（編修）
deploy/    Dockerfile
```

## 安裝與執行

### 後端
```bash
uv sync                  # 依 pyproject.toml / uv.lock 建立 .venv 並安裝相依（含 dev）
cp .env.example .env     # 填 GEMINI_API_KEY、ADMIN_PASSWORD、SECRET_KEY、PUBLIC_BASE_URL
uv run uvicorn backend.app:app --port 8000 --reload
```
> 需先安裝 [uv](https://docs.astral.sh/uv/)（`curl -LsSf https://astral.sh/uv/install.sh | sh`）。相依定義在 `pyproject.toml`，鎖定版本在 `uv.lock`。

### 前端
```bash
cd web && npm install
npm run dev        # 開發：http://localhost:5173（/api 代理到 8000）
# 或
npm run build      # 產生 web/dist，改開 http://localhost:8000（後端一併提供，含 SPA 深連結）
```

## 內容工作流程（後台）

1. `/admin` 登入（`ADMIN_PASSWORD`）。
2. `/admin/ingest`：上傳 LINE 匯出 `.txt` → 搜尋、勾選要用的訊息 → 「產生文章草稿」（送 Gemini）。
3. 自動建立草稿並跳到編輯器，你可改標題、摘錄、封面、內文（Markdown，即時預覽）。
4. 按「發佈」→ 成為最新文章 → 公開網站與 widget 會顯示。

## API

**公開**：`GET /api/articles`、`GET /api/articles/latest`、`GET /api/articles/{slug}`
**後台（Bearer token）**：`POST /api/admin/login`、`/import`、`/messages`、`/draft`、`/articles`(建立/更新)、`/articles/{id}/publish`、`/unpublish`、`DELETE`。

## 部署（Phase C：Railway）

單一服務，FastAPI 同時提供 API + 前端。
```bash
docker build -f deploy/Dockerfile -t hs-story .
docker run -p 8000:8000 -v hs_data:/data \
  -e ADMIN_PASSWORD=... -e SECRET_KEY=... -e GEMINI_API_KEY=... \
  -e PUBLIC_BASE_URL=https://your-domain hs-story
```
Railway：連 GitHub repo → 用 `deploy/Dockerfile` → 掛一個 volume 到 `/data`（SQLite 持久化）→ 設上述環境變數。`PUBLIC_BASE_URL` 設成部署後的網址，文章連結與 widget deep-link 才正確。

## 測試
```bash
uv run pytest -q      # parser / articles / auth / API（draft 以 mock 取代 Gemini）
```

## 隱私與安全
- 資料存本機/自架 SQLite；只有後台選取要產草稿的訊息會送到 Gemini API。
- 後台以密碼 + 簽章 token 保護；務必把 `SECRET_KEY` 設為隨機長字串、`ADMIN_PASSWORD` 設強密碼。
