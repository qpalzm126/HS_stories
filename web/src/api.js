const BASE = '/api'

const getToken = () => localStorage.getItem('hs_token') || ''
const setToken = (t) => localStorage.setItem('hs_token', t)
const clearToken = () => localStorage.removeItem('hs_token')

async function toJson(res) {
  if (res.status === 401) {
    clearToken()
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
  // ---- 公開 ----
  articles: (limit = 50) => fetch(`${BASE}/articles?limit=${limit}`).then(toJson),
  latest: () => fetch(`${BASE}/articles/latest`).then(toJson),
  article: (slug) => fetch(`${BASE}/articles/${encodeURIComponent(slug)}`).then(toJson),

  // ---- 登入 ----
  isLoggedIn: () => !!getToken(),
  logout: clearToken,
  login: (password) =>
    fetch(`${BASE}/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    })
      .then(toJson)
      .then((d) => {
        setToken(d.token)
        return d
      }),

  // ---- 後台文章 ----
  adminArticles: () => fetch(`${BASE}/admin/articles`, { headers: authHeaders() }).then(toJson),
  adminArticle: (id) => fetch(`${BASE}/admin/articles/${id}`, { headers: authHeaders() }).then(toJson),
  saveArticle: (a) =>
    fetch(`${BASE}/admin/articles`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(a),
    }).then(toJson),
  publish: (id) => fetch(`${BASE}/admin/articles/${id}/publish`, { method: 'POST', headers: authHeaders() }).then(toJson),
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
}
