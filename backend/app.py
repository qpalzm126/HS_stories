"""FastAPI：公開 API（給網站與 widget）+ 後台 API（發文用）+ 提供前端。

啟動（開發）：
    uvicorn backend.app:app --reload
前端開發：web/ 執行 npm run dev（5173，/api 代理到 8000）。
或 web/ 執行 npm run build 後，本後端直接在 / 提供 web/dist（含 SPA 深連結）。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import Body, Depends, FastAPI, File, Header, HTTPException, Query, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from backend import articles, auth, db, importer, summarizer  # noqa: E402

MAX_DRAFT_MESSAGES = 3000


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="聖靈故事", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 後台驗證 -----------------------------------------------------------------


def require_admin(authorization: str | None = Header(None)) -> None:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    if not auth.verify_token(token):
        raise HTTPException(401, "未授權，請重新登入")


# ============ 公開 API（免驗證，給網站與 widget）============


@app.get("/api/articles")
def public_articles(q: str | None = None, limit: int = Query(50, le=500), offset: int = 0):
    rows = db.list_articles(published_only=True, limit=limit, offset=offset, q=q)
    return [articles.public_article(r) for r in rows]


@app.get("/api/articles/latest")
def public_latest():
    row = db.get_latest_article()
    if not row:
        raise HTTPException(404, "尚無已發佈的文章")
    return articles.public_article(row, full=True)


@app.get("/api/articles/{slug}")
def public_article_by_slug(slug: str):
    row = db.get_article_by_slug(slug, published_only=True)
    if not row:
        raise HTTPException(404, "找不到這篇文章")
    return articles.public_article(row, full=True)


# ============ 後台 API（需 Bearer token）============


class LoginReq(BaseModel):
    password: str


@app.post("/api/admin/login")
def admin_login(req: LoginReq):
    if not auth.check_password(req.password):
        raise HTTPException(401, "密碼錯誤")
    return {"token": auth.make_token()}


@app.post("/api/admin/import", dependencies=[Depends(require_admin)])
async def admin_import(file: UploadFile = File(...)):
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "檔案是空的")
    default_name = Path(file.filename or "未命名對話").stem
    return importer.import_bytes(raw, source_file=file.filename or "", default_conversation=default_name)


@app.get("/api/admin/conversations", dependencies=[Depends(require_admin)])
def admin_conversations():
    return db.list_conversations()


@app.get("/api/admin/senders", dependencies=[Depends(require_admin)])
def admin_senders(conversation: str | None = None):
    return db.list_senders(conversation)


@app.get("/api/admin/messages", dependencies=[Depends(require_admin)])
def admin_messages(
    q: str | None = None,
    conversation: str | None = None,
    sender: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(300, le=1000),
    offset: int = 0,
):
    msgs = db.query_messages(
        q=q, conversation=conversation, sender=sender,
        date_from=date_from, date_to=date_to, limit=limit, offset=offset,
    )
    return {"count": len(msgs), "messages": msgs}


class DraftReq(BaseModel):
    message_ids: list[int] | None = None
    q: str | None = None
    conversation: str | None = None
    sender: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    limit: int = MAX_DRAFT_MESSAGES


@app.post("/api/admin/draft", dependencies=[Depends(require_admin)])
def admin_draft(req: DraftReq):
    if req.message_ids:
        msgs = db.get_messages_by_ids(req.message_ids[:MAX_DRAFT_MESSAGES])
    else:
        msgs = db.query_messages(
            q=req.q, conversation=req.conversation, sender=req.sender,
            date_from=req.date_from, date_to=req.date_to, limit=min(req.limit, MAX_DRAFT_MESSAGES),
        )
    if not msgs:
        raise HTTPException(404, "沒有可用來產生草稿的訊息")
    try:
        draft = summarizer.draft_article(msgs)
    except summarizer.SummarizerError as e:
        raise HTTPException(503, str(e))
    return {"message_count": len(msgs), "draft": draft}


class DraftFromTextReq(BaseModel):
    text: str


@app.post("/api/admin/draft-from-text", dependencies=[Depends(require_admin)])
def admin_draft_from_text(req: DraftFromTextReq):
    """複製貼上捷徑：直接把貼上的一段對話文字產成草稿（不經匯入與訊息挑選）。"""
    if not req.text or not req.text.strip():
        raise HTTPException(400, "請貼上要產生草稿的內容")
    try:
        draft = summarizer.draft_from_text(req.text)
    except summarizer.SummarizerError as e:
        raise HTTPException(503, str(e))
    return {"draft": draft}


class ArticleIn(BaseModel):
    id: int | None = None
    title: str
    body: str = ""
    excerpt: str = ""
    cover_url: str = ""
    source_ref: str = ""


@app.post("/api/admin/articles", dependencies=[Depends(require_admin)])
def admin_save_article(a: ArticleIn):
    if a.id:
        if not db.get_article_by_id(a.id):
            raise HTTPException(404, "找不到文章")
        db.update_article(
            a.id, title=a.title, body=a.body, excerpt=a.excerpt,
            cover_url=a.cover_url, source_ref=a.source_ref,
        )
        return db.get_article_by_id(a.id)
    slug = articles.unique_slug(a.title)
    new_id = db.create_article(
        slug=slug, title=a.title, body=a.body, excerpt=a.excerpt,
        cover_url=a.cover_url, source_ref=a.source_ref, status="draft",
    )
    return db.get_article_by_id(new_id)


@app.get("/api/admin/articles", dependencies=[Depends(require_admin)])
def admin_list_articles(
    q: str | None = None,
    status: str | None = None,
    limit: int = Query(20, le=500),
    offset: int = 0,
):
    return {
        "total": db.count_articles_admin(q=q, status=status),
        "items": db.list_articles_admin(q=q, status=status, limit=limit, offset=offset),
    }


@app.get("/api/admin/articles/{article_id}", dependencies=[Depends(require_admin)])
def admin_get_article(article_id: int):
    row = db.get_article_by_id(article_id)
    if not row:
        raise HTTPException(404, "找不到文章")
    return row


class PublishReq(BaseModel):
    published_at: str | None = None


@app.post("/api/admin/articles/{article_id}/publish", dependencies=[Depends(require_admin)])
def admin_publish(article_id: int, req: PublishReq | None = Body(None)):
    if not db.get_article_by_id(article_id):
        raise HTTPException(404, "找不到文章")
    db.publish_article(article_id, published_at=(req.published_at if req else None))
    return db.get_article_by_id(article_id)


@app.post("/api/admin/articles/{article_id}/unpublish", dependencies=[Depends(require_admin)])
def admin_unpublish(article_id: int):
    if not db.get_article_by_id(article_id):
        raise HTTPException(404, "找不到文章")
    db.unpublish_article(article_id)
    return db.get_article_by_id(article_id)


@app.delete("/api/admin/articles/{article_id}", dependencies=[Depends(require_admin)])
def admin_delete(article_id: int):
    db.delete_article(article_id)
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"ok": True, "fts": db.FTS_ENABLED}


# ---- 前端靜態檔（含 SPA 深連結 fallback）-------------------------------------
# 置於所有 API 路由之後：/api/* 由上面處理，其餘路徑交給前端。

_DIST = Path(__file__).parent.parent / "web" / "dist"

if (_DIST / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        candidate = _DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
else:
    @app.get("/")
    def root():
        return {"message": "後端運作中，但前端尚未 build（web/dist）。開發時請於 web/ 執行 npm run dev。", "docs": "/docs"}
