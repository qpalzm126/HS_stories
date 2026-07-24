import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import AdminShortcut from '../components/AdminShortcut.jsx'

const PAGE_SIZE = 20 // 每頁筆數（數字分頁）

const SORTS = [
  { value: 'published_desc', label: '最新在前' },
  { value: 'published_asc', label: '最舊在前' },
]

// 產生頁碼列：首頁、末頁、當前 ±2，其餘以 '…' 省略。
function pageNumbers(current, totalPages) {
  const span = 2
  const set = new Set([1, totalPages])
  for (let p = current - span; p <= current + span; p++) {
    if (p >= 1 && p <= totalPages) set.add(p)
  }
  const sorted = [...set].sort((a, b) => a - b)
  const out = []
  let prev = 0
  for (const p of sorted) {
    if (p - prev > 1) out.push('…')
    out.push(p)
    prev = p
  }
  return out
}

export default function Home() {
  const [items, setItems] = useState(null)
  const [total, setTotal] = useState(0)
  const [err, setErr] = useState('')
  const [q, setQ] = useState('')
  const [dq, setDq] = useState('') // debounced query
  const [sort, setSort] = useState('published_desc')
  const [page, setPage] = useState(1) // 1-based

  // 打字時 debounce，避免每個字都打 API
  useEffect(() => {
    const t = setTimeout(() => setDq(q.trim()), 250)
    return () => clearTimeout(t)
  }, [q])

  // 換搜尋字或排序 → 回到第 1 頁
  useEffect(() => {
    setPage(1)
  }, [dq, sort])

  // 總數（算總頁數用；只跟搜尋字有關）
  useEffect(() => {
    let ignore = false
    api
      .articlesCount({ q: dq })
      .then((d) => { if (!ignore) setTotal(d.total || 0) })
      .catch(() => { if (!ignore) setTotal(0) })
    return () => { ignore = true }
  }, [dq])

  // 當頁資料（ignore 旗標避免舊請求覆蓋新結果）
  useEffect(() => {
    let ignore = false
    setItems(null)
    setErr('')
    api
      .articles({ q: dq, sort, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
      .then((list) => { if (!ignore) setItems(list) })
      .catch((e) => { if (!ignore) setErr(String(e.message || e)) })
    return () => { ignore = true }
  }, [dq, sort, page])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const go = useCallback((p) => {
    setPage((cur) => {
      const next = Math.min(Math.max(1, p), totalPages)
      if (next !== cur) window.scrollTo({ top: 0, behavior: 'smooth' })
      return next
    })
  }, [totalPages])

  return (
    <div className="site">
      <header className="site-head">
        <h1>聖靈故事</h1>
        <p className="site-nav"><Link to="/calendar">📅 日曆瀏覽</Link></p>
      </header>

      <div className="site-search">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="搜尋標題或內文關鍵字…"
          aria-label="搜尋文章"
        />
      </div>

      {err && <p className="error">{err}</p>}

      {items === null ? (
        <p className="muted">載入中…</p>
      ) : total === 0 ? (
        <p className="muted">{dq ? `找不到含「${dq}」的文章。` : '目前還沒有文章。'}</p>
      ) : (
        <>
          <div className="list-toolbar">
            <span className="muted">
              {dq ? `找到 ${total} 篇含「${dq}」的文章` : `共 ${total} 篇`}
            </span>
            <label className="sort-select">
              排序
              <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="排序方式">
                {SORTS.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="cards">
            {items.map((a) => (
              <Link className="card" to={`/article/${a.slug}`} key={a.slug}>
                {a.cover_url && <img src={a.cover_url} alt="" loading="lazy" />}
                <div className="card-body">
                  <h2>{a.title}</h2>
                  {a.excerpt && <p>{a.excerpt}</p>}
                  <time className="muted">{(a.published_at || '').slice(0, 10)}</time>
                </div>
              </Link>
            ))}
          </div>

          {totalPages > 1 && (
            <nav className="pagination" aria-label="分頁">
              <button className="btn sm" onClick={() => go(page - 1)} disabled={page <= 1}>‹ 上一頁</button>
              {pageNumbers(page, totalPages).map((p, i) =>
                p === '…' ? (
                  <span key={`e${i}`} className="page-ellipsis">…</span>
                ) : (
                  <button
                    key={p}
                    className={'page-num' + (p === page ? ' active' : '')}
                    onClick={() => go(p)}
                    aria-current={p === page ? 'page' : undefined}
                  >
                    {p}
                  </button>
                )
              )}
              <button className="btn sm" onClick={() => go(page + 1)} disabled={page >= totalPages}>下一頁 ›</button>
            </nav>
          )}
        </>
      )}

      <footer className="site-foot">
        <Link to="/admin">後台</Link>
      </footer>

      <AdminShortcut />
    </div>
  )
}
