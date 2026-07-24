const BASE = '/api'

const getToken = () => localStorage.getItem('hs_token') || ''
const setToken = (t) => localStorage.setItem('hs_token', t)
const clearToken = () => localStorage.removeItem('hs_token')

// 使用者資訊（非敏感：username / server / is_admin），給 UI 判斷用。
const getUser = () => {
  try {
    return JSON.parse(localStorage.getItem('hs_user') || 'null')
  } catch {
    return null
  }
}
const setUser = (u) => localStorage.setItem('hs_user', JSON.stringify(u))
const clearUser = () => localStorage.removeItem('hs_user')

function clearAuth() {
  clearToken()
  clearUser()
}

async function toJson(res) {
  if (res.status === 401) {
    clearAuth()
    throw new Error('未授權，請重新登入')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const b = await res.json()
      detail = b.detail || JSON.stringify(b)
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json()
}

const authHeaders = (extra = {}) => ({ ...extra, Authorization: `Bearer ${getToken()}` })

function clean(o) {
  const r = {}
  for (const k in o) if (o[k] !== '' && o[k] != null) r[k] = o[k]
  return r
}

export const api = {
  // ---- 文章（整站需登入，帶 Bearer token）----
  articles: (params = {}) =>
    fetch(`${BASE}/articles?` + new URLSearchParams(clean(params)), { headers: authHeaders() }).then(toJson),
  articlesCount: (params = {}) =>
    fetch(`${BASE}/articles/count?` + new URLSearchParams(clean(params)), { headers: authHeaders() }).then(toJson),
  latest: () => fetch(`${BASE}/articles/latest`, { headers: authHeaders() }).then(toJson),
  article: (slug) =>
    fetch(`${BASE}/articles/${encodeURIComponent(slug)}`, { headers: authHeaders() }).then(toJson),

  // ---- 登入 ----
  isLoggedIn: () => !!getToken(),
  currentUser: getUser,
  isAdmin: () => !!(getUser() && getUser().is_admin),
  logout: clearAuth,
  login: ({ server, username, password }) =>
    fetch(`${BASE}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ server, username, password }),
    })
      .then(toJson)
      .then((d) => {
        setToken(d.token)
        setUser({ username: d.username, server: d.server, is_admin: d.is_admin })
        return d
      }),
  me: () =>
    fetch(`${BASE}/me`, { headers: authHeaders() })
      .then(toJson)
      .then((d) => {
        setUser(d)
        return d
      }),

  // ---- 後台文章 ----
  adminArticles: (params = {}) =>
    fetch(`${BASE}/admin/articles?` + new URLSearchParams(clean(params)), { headers: authHeaders() }).then(toJson),
  adminArticle: (id) => fetch(`${BASE}/admin/articles/${id}`, { headers: authHeaders() }).then(toJson),
  saveArticle: (a) =>
    fetch(`${BASE}/admin/articles`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(a),
    }).then(toJson),
  publish: (id, publishedAt) =>
    fetch(`${BASE}/admin/articles/${id}/publish`, {
      method: 'POST',
      headers: publishedAt ? authHeaders({ 'Content-Type': 'application/json' }) : authHeaders(),
      body: publishedAt ? JSON.stringify({ published_at: publishedAt }) : undefined,
    }).then(toJson),
  unpublish: (id) => fetch(`${BASE}/admin/articles/${id}/unpublish`, { method: 'POST', headers: authHeaders() }).then(toJson),
  remove: (id) => fetch(`${BASE}/admin/articles/${id}`, { method: 'DELETE', headers: authHeaders() }).then(toJson),

  // ---- 後台：從 LINE 產內容 ----
  importFile: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return fetch(`${BASE}/admin/import`, { method: 'POST', headers: authHeaders(), body: fd }).then(toJson)
  },
  conversations: () => fetch(`${BASE}/admin/conversations`, { headers: authHeaders() }).then(toJson),
  senders: (c) =>
    fetch(`${BASE}/admin/senders${c ? `?conversation=${encodeURIComponent(c)}` : ''}`, { headers: authHeaders() }).then(toJson),
  messages: (f) => fetch(`${BASE}/admin/messages?` + new URLSearchParams(clean(f)), { headers: authHeaders() }).then(toJson),
  draft: (payload) =>
    fetch(`${BASE}/admin/draft`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(clean(payload)),
    }).then(toJson),
  draftFromText: (payload) =>
    fetch(`${BASE}/admin/draft-from-text`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(clean(payload)),
    }).then(toJson),
}
