# 登入功能實作計劃書（hs-story）

> 目的：為 hs-story 加上「登入」。使用者用 **HeavensBride / TCGM 的既有論壇帳密**代理登入，
> **整站需登入才能瀏覽**，並以**環境變數白名單**決定誰是 admin（取代現有單一密碼）。
> 參考來源：`/Users/leon.chen/code/woRds3`（Flutter App，只有 client 端代理登入邏輯，無自有後端）。
>
> 本文件是給後續實作用的規格書。實作前先看「§0 已定案決策」與「§8 未決事項」。

---

## §0 已定案決策（使用者確認過）

1. **登入來源**：兩者都支援。登入頁可選 server（`heavensbride` 或 `tcgm`），用該站帳密代理登入。
2. **範圍**：**整站都要登入才能看**（公開頁面 + App 都要），不是只擋後台。
3. **admin 指定**：**環境變數白名單**，格式 `server:username`（避免兩站同名衝突），
   例：`ADMIN_USERS=heavensbride:alice,tcgm:bob`。**移除**現有 `ADMIN_PASSWORD` 單一密碼登入。
4. **Token**：沿用現有 `itsdangerous` 簽章 token（Bearer），payload 改存使用者身分；web 與 app 一致。
5. **順序**：先 **後端 + web**、驗證後再做 **app**（app 為第二階段）。

### 安全底線（務必遵守）
- **絕不儲存使用者的論壇密碼**（DB、log、token 都不放）。密碼只在登入當下轉發給外部站驗證，用完即棄。
- Token 只放**非敏感身分資訊**（username、server、is_admin），並有有效期。
- 代理登入一律走 **HTTPS**。

---

## §1 現況（改造前）

- **後端**：FastAPI + SQLite（`backend/`）。認證在 `backend/auth.py`：
  - `check_password()` 比對 `ADMIN_PASSWORD`；`make_token()` 簽 `{"role":"admin"}`；`verify_token()` 驗簽（`itsdangerous.URLSafeTimedSerializer`，salt `hs-admin`，7 天）。
  - `SECRET_KEY` 環境變數簽 token。
- **後端 route**（`backend/app.py`）：
  - 公開（目前**免驗證**）：`GET /api/articles`、`/api/articles/count`、`/api/articles/latest`、`/api/articles/{slug}`。
  - 後台（`Depends(require_admin)`）：`/api/admin/login`、`/api/admin/articles...` 等。`require_admin` 讀 `Authorization: Bearer` 呼叫 `verify_token`。
- **Web**（React + Vite，`web/src/`）：
  - `api.js`：token 存 `localStorage` 的 `hs_token`；`authHeaders()` 帶 `Authorization: Bearer`；`login(password)` 打 `/api/admin/login`。
  - Router 在 `main.jsx`；公開頁 `pages/Home.jsx`、`pages/Article.jsx`、`pages/Calendar.jsx`；後台 `pages/admin/{Login,Dashboard,Editor,Ingest}.jsx`。
  - 已有右下角浮動「管理」鈕 `components/AdminShortcut.jsx`（`api.isLoggedIn()` 才顯示）。
- **App**（Flutter，`app/`）：目前**無登入**，`lib/api.dart` 只讀公開 API。

---

## §2 架構總覽（改造後）

```
使用者 → [Web 登入頁 / App 登入畫面]  選 server + 帳密
        → POST /api/login {server, username, password}
        → 後端代理登入外部站（TCGM 表單 / HeavensBride SMF）
            成功 → is_admin = (f"{server}:{username}" 在 ADMIN_USERS)
                 → 簽 itsdangerous token {u, s, a} 回傳
            失敗 → 401
        → 前端存 token；之後所有 /api 請求帶 Bearer
        → 後端所有 /api/articles* 需 require_user；/api/admin/* 需 require_admin
```

- 代理登入**只在後端做**（瀏覽器/CORS 無法直接打外部站）。
- 登入只為「驗證此人有有效的論壇帳號」；驗過就發自己的 token，**不需保留外部站 cookie**。

---

## §3 外部站登入協定（複製自 woRds3，附原始檔行號）

> 這兩套是實作 `backend/auth.py` 代理登入的依據。用 `httpx`（同步 `httpx.Client`，需處理 cookie 與多步驟）。

### 3a. TCGM（`https://ms.tcgm.tw`，表單式）
參考 `woRds3/lib/screens/login_page.dart:76-104`、`lib/services/session_manager.dart:84-91`。

1. `GET https://ms.tcgm.tw/` → 取初始 `Set-Cookie`（sessionid）。
2. `POST https://ms.tcgm.tw/welcome/login`
   - Header：`Content-Type: application/x-www-form-urlencoded`，帶上一步 cookie。
   - Body：`account=<username>&pwd=<password>`（**明文密碼直接送外部站**，這是該站的協定）。
   - 帶新的 `Set-Cookie`。
3. **驗證成功**：`GET https://ms.tcgm.tw/home/`（帶 cookie）→ status 200 **且** body 含字串 `/welcome/logout`。
   - 失敗（沒有該字串或非 200）視為帳密錯誤 → 回 401。

### 3b. HeavensBride（`https://heavensbride.org`，SMF 論壇 SHA1 挑戰式）
參考 `woRds3/lib/services/heavens_bride_service.dart:156-246`（登入）、`:83-119`（解析 token）、`:127-136`（算 hash）、`:384-397`（驗證）。

1. `GET https://heavensbride.org/index.php?action=login` → 取 HTML + `Set-Cookie`。
2. **從 HTML 解析 sessionId / CSRF 欄位**（`parseSessionToken`）：
   - 找所有 `<input type="hidden">`，取 **value 為 32 字元 hex** 的那個；**排除** name 為 `hash_passwrd` 的。
   - 該 input 的 **name = 隨機 CSRF 欄位名**、**value = sessionId**（32 hex）。
   - 後端可用正則：`<input\s+type="hidden"\s+name="([^"]+)"\s+value="([0-9a-f]{32})"`（實測時再微調；SMF 各版屬性順序可能不同，建議用 HTML parser 較穩，見 §5 相依）。
3. **算密碼雜湊**（SMF 標準，`calculateHash`）：
   ```
   inner       = sha1( lower(username) + password )   # hex
   hash_passwrd = sha1( inner + sessionId )            # hex
   ```
   （`sessionId` 就是上一步那個 32-hex value。用 Python `hashlib.sha1(...).hexdigest()`。）
4. `POST https://heavensbride.org/index.php?action=login2`（帶步驟 1 cookie，urlencoded）：
   - `user=<username>`
   - `passwrd=`（**空字串**，明文密碼不送）
   - `cookielength=-1`
   - `hash_passwrd=<步驟3算出>`
   - `<隨機CSRF欄位名>=<sessionId>`
5. **判斷**：SMF 失敗時仍回 200，body 會含 `Password incorrect` → 視為失敗。成功 → 取新的 `Set-Cookie`。
6. （可選）**再驗證**：`GET https://heavensbride.org/index.php`（帶 cookie）→ body 含 `action=logout` 才算真的登入。

> 註：woRds3 有測試 `woRds3/test/heavens_bride_logic_test.dart` 覆蓋 `parseSessionToken`/`calculateHash`，可當規格對照與單元測試藍本。

---

## §4 後端實作（FastAPI）— 第一階段

### 4.1 `backend/auth.py`
- 保留 `_serializer()`（`itsdangerous`）。**移除或停用** `check_password()` / `ADMIN_PASSWORD` 相關（改用代理登入）。
- 新增設定讀取：
  ```python
  def _admin_users() -> set[str]:
      raw = os.environ.get("ADMIN_USERS", "")
      return {x.strip().lower() for x in raw.split(",") if x.strip()}
  def is_admin_user(server: str, username: str) -> bool:
      return f"{server}:{username}".lower() in _admin_users()
  ```
- token payload 改為 `{"u": username, "s": server, "a": is_admin}`：
  ```python
  def make_token(username, server, is_admin) -> str:
      return _serializer().dumps({"u": username, "s": server, "a": bool(is_admin)})
  def verify_token(token):  # 回 payload dict 或 None
      if not token: return None
      try:
          return _serializer().loads(token, max_age=TOKEN_MAX_AGE)
      except (BadSignature, SignatureExpired):
          return None
  ```
- 代理登入函式（用 `httpx`）：
  ```python
  def login_tcgm(username: str, password: str) -> bool: ...        # §3a
  def login_heavensbride(username: str, password: str) -> bool: ... # §3b
  def proxy_login(server: str, username: str, password: str) -> bool:
      if server == "tcgm": return login_tcgm(username, password)
      if server == "heavensbride": return login_heavensbride(username, password)
      return False
  ```
  - 逾時要設（如 15s），外部站掛掉時回 502/503 而非 500。
  - 解析 HTML 建議用 parser（見 §5）。

### 4.2 `backend/app.py`
- FastAPI dependencies：
  ```python
  def require_user(authorization: str | None = Header(None)) -> dict:
      payload = auth.verify_token(_bearer(authorization))
      if not payload: raise HTTPException(401, "請先登入")
      return payload
  def require_admin(user: dict = Depends(require_user)) -> dict:
      if not user.get("a"): raise HTTPException(403, "需要管理員權限")
      return user
  ```
  （`_bearer()` 從 `Authorization: Bearer xxx` 取 token；沿用現有解析。）
- 新端點：
  ```python
  class LoginReq(BaseModel):
      server: str            # "heavensbride" | "tcgm"
      username: str
      password: str
  @app.post("/api/login")
  def login(req: LoginReq):
      if req.server not in ("heavensbride", "tcgm"):
          raise HTTPException(400, "server 不支援")
      if not auth.proxy_login(req.server, req.username, req.password):
          raise HTTPException(401, "帳號或密碼錯誤")
      is_admin = auth.is_admin_user(req.server, req.username)
      token = auth.make_token(req.username, req.server, is_admin)
      return {"token": token, "username": req.username, "server": req.server, "is_admin": is_admin}
  @app.get("/api/me")
  def me(user: dict = Depends(require_user)):
      return {"username": user["u"], "server": user["s"], "is_admin": user.get("a", False)}
  ```
- **整站需登入**：對這四個加 `Depends(require_user)`：
  `GET /api/articles`、`GET /api/articles/count`、`GET /api/articles/latest`、`GET /api/articles/{slug}`。
- **後台**：`/api/admin/*` 全部把 `require_admin` 換成新的（讀 token payload 的 `a`）。**移除** `/api/admin/login`（改用 `/api/login`）。
- 保持向後相容？不需要——舊 `ADMIN_PASSWORD` 流程整個換掉。

### 4.3 環境變數（更新 `.env.example`、`render.yaml`）
- 新增 `ADMIN_USERS`（如 `heavensbride:alice,tcgm:bob`）。
- 保留 `SECRET_KEY`。移除 `ADMIN_PASSWORD`。

### 4.4 後端測試（`backend/tests/`）
- `is_admin_user()` 白名單解析。
- `proxy_login` 用 `httpx` 的 mock（`respx` 或 monkeypatch）測 TCGM / HeavensBride 的成功/失敗判斷；HeavensBride 的 `calculateHash` 對照 woRds3 測試值。
- 受保護端點：無 token → 401；有 user token 非 admin → 打 `/api/admin/*` 得 403；admin token → 通過。

---

## §5 相依套件（後端）
- **`httpx`**：代理登入的 HTTP client（FastAPI 生態常見；確認 `pyproject.toml` 是否已有，沒有就 `uv add httpx`）。
- HTML 解析：優先看專案是否已有（`backend/parser.py` 可能用了 `beautifulsoup4`/`lxml`）。有就沿用；否則用正則解 SMF 隱藏欄位（§3b 步驟 2）。
- `hashlib`（標準庫，SMF SHA1）、`itsdangerous`（已有）。

---

## §6 Web 實作（React + Vite）— 第一階段

### 6.1 `web/src/api.js`
- 移除 `login(password)` 舊版；新增：
  ```js
  login: ({ server, username, password }) =>
    fetch(`${BASE}/login`, { method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ server, username, password }) })
      .then(toJson).then((d) => { setToken(d.token); return d }),
  me: () => fetch(`${BASE}/me`, { headers: authHeaders() }).then(toJson),
  ```
  - `authHeaders()`、`hs_token` localStorage、`toJson`（401 清 token）沿用現有。
  - 公開列表/文章 API 已會帶 `authHeaders()`？**目前沒帶**（公開 API 之前免驗證）。→ 把 `articles`/`articlesCount`/`latest`/`article` 都改成帶 `authHeaders()`。
- 另存使用者資訊（`is_admin`/`username`）到 localStorage 或每次打 `/api/me`，給 UI 判斷用。

### 6.2 登入頁（改造 `pages/admin/Login.jsx` → 全站登入頁，移到 `/login`）
- 欄位：**server 單選**（HeavensBride / TCGM，radio 或 select）、username、password、送出按鈕（loading/disable）、錯誤訊息。
- 送出 → `api.login({server,username,password})` → 成功導回原本要去的頁（或首頁）。
- **樣式用本 repo 風格**（金色主題 `--accent`、`.btn.primary`、`.site-search` 那種圓角輸入框），**不要照抄 woRds3 外觀**。可加一個 `.login` 區塊樣式到 `styles.css`。

### 6.3 路由守衛（`main.jsx`）
- 新增 `components/ProtectedRoute.jsx`：無 token → `<Navigate to="/login" replace state={{from}}/>`；（可選）掛載時打 `/api/me` 驗 token 有效，401 就清 token 導登入。
- **所有頁面包在 ProtectedRoute 內**（Home、Article、Calendar、admin/*）。`/login` 是唯一免登入路由。
- admin 頁面（Dashboard/Editor/Ingest）另包一層 admin 檢查：非 `is_admin` → 導首頁或顯示「需要管理員」。
- `AdminShortcut.jsx`：改成 `is_admin` 才顯示（目前是 `isLoggedIn`）。
- 加「登出」：清 `hs_token` + 使用者資訊 → 導 `/login`。放在 header 或 AdminShortcut 附近。

### 6.4 Web 驗證
- 本機：`make backend`（8000）+ `make web`（5173，proxy /api→8000）。
- 先 seed 或用實際帳號登入；未登入直接開首頁應被導到 `/login`。
- 用非 admin 帳號登入 → 看得到內容、但進不了 `/admin`；admin 白名單帳號 → 能進後台。

---

## §7 App 實作（Flutter）— 第二階段

### 7.1 套件
- `flutter_secure_storage`（存 token；比 shared_preferences 安全）。加到 `app/pubspec.yaml`。

### 7.2 `app/lib/`
- `auth_service.dart`（新）：`login(server, username, password)` 打 `/api/login` 存 token；`token()`、`logout()`、`isLoggedIn()`。
- `api.dart`：所有請求帶 `Authorization: Bearer <token>`；收到 401 → 清 token 並通知導回登入。
- `login_screen.dart`（新）：server 單選 + 帳密 + 登入鈕，樣式沿用 App 既有 `theme.dart`。
- `main.dart`：啟動時 `isLoggedIn()` 決定進 `HomeScreen` 或 `LoginScreen`；`HomeScreen` 加登出。

### 7.3 Widget / 背景更新（重要陷阱）
- 整站需登入後，`/api/articles/latest` 也要 token。`widget_service.dart` 的背景 isolate（workmanager）與 iOS/Android widget 更新都要能拿到 token。
  - 背景 isolate 讀 token：`flutter_secure_storage` 在背景 isolate 可能受限，評估改用 `shared_preferences`（token 是簽章字串、非密碼，風險可接受）或確認 secure_storage 背景可用。
  - 未登入 / token 失效時，背景更新就跳過（widget 維持舊資料），不要崩潰。
- 這塊留到 app 階段實測時處理，先確保前景登入流程可用。

---

## §8 未決 / 需人工

- **測試帳號**：實作者（或你）需要一組 HeavensBride 與/或 TCGM 的**有效帳密**，才能真的把代理登入跑通。單元測試可用 mock，但端到端驗證需真帳號。
- **外部站協定變動風險**：TCGM/HeavensBride 若改版（欄位名、成功頁字串），代理登入會壞。實作時以 woRds3 現行邏輯為準，並把「成功判斷字串」等集中成常數方便日後改。
- **HeavensBride CSRF 解析**：SMF 版本差異可能讓隱藏欄位屬性順序不同；若正則抓不到就改用 HTML parser。
- **App 背景 token**：見 §7.3。

---

## §9 建議任務順序（可當 checklist）

**後端**
- [ ] `auth.py`：`ADMIN_USERS` 解析 + `is_admin_user()`
- [ ] `auth.py`：`make_token/verify_token` 改存 `{u,s,a}`
- [ ] `auth.py`：`login_tcgm` / `login_heavensbride` / `proxy_login`（httpx）
- [ ] `app.py`：`require_user` / `require_admin`（讀 payload）
- [ ] `app.py`：`POST /api/login`、`GET /api/me`
- [ ] `app.py`：四個 `/api/articles*` 加 `require_user`
- [ ] `app.py`：`/api/admin/*` 改 `require_admin`，移除 `/api/admin/login`
- [ ] `.env.example` / `render.yaml`：加 `ADMIN_USERS`，移除 `ADMIN_PASSWORD`
- [ ] 後端測試（白名單、hash、受保護端點 401/403）

**Web**
- [ ] `api.js`：`login({server,username,password})`、`me()`；公開 API 帶 `authHeaders()`
- [ ] 登入頁（server 單選 + 帳密，本 repo 樣式），路由 `/login`
- [ ] `ProtectedRoute` 包住所有頁；admin 頁另檢查 `is_admin`
- [ ] `AdminShortcut` 改 `is_admin` 才顯示；加登出
- [ ] 本機端到端驗證

**App（第二階段）**
- [ ] `flutter_secure_storage`；`auth_service.dart`
- [ ] `api.dart` 帶 Bearer + 401 處理
- [ ] `login_screen.dart`；`main.dart` 啟動導向
- [ ] widget/背景更新帶 token（§7.3）
- [ ] 模擬器端到端驗證

---

## §10 參考檔案速查
- woRds3 TCGM 登入：`woRds3/lib/screens/login_page.dart:76-104`
- woRds3 TCGM 驗證：`woRds3/lib/services/session_manager.dart:84-91`
- woRds3 HeavensBride 登入：`woRds3/lib/services/heavens_bride_service.dart:156-246`
- woRds3 解析 token：`heavens_bride_service.dart:83-119`
- woRds3 算 hash：`heavens_bride_service.dart:127-136`
- woRds3 HeavensBride 驗證：`heavens_bride_service.dart:384-397`
- woRds3 登入邏輯測試：`woRds3/test/heavens_bride_logic_test.dart`
- hs-story 現有 auth：`backend/auth.py`
- hs-story 現有 route：`backend/app.py`（公開 §59 起、後台 §81 起）
- hs-story web api：`web/src/api.js`；router：`web/src/main.jsx`
