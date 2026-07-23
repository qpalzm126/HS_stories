import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import AdminShortcut from '../components/AdminShortcut.jsx'

const PAGE = 100 // 每批載入筆數（後端公開 API limit 上限 200，取 100 分批較穩）

export default function Home() {
  const [items, setItems] = useState(null)
  const [err, setErr] = useState('')
  const [q, setQ] = useState('')
  const [dq, setDq] = useState('') // debounced query
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  // 打字時 debounce，避免每個字都打 API
  useEffect(() => {
    const t = setTimeout(() => setDq(q.trim()), 250)
    return () => clearTimeout(t)
  }, [q])

  useEffect(() => {
    setItems(null)
    setErr('')
    setHasMore(false)
    if (dq) {
      // 有關鍵字：一次抓（上限 200，對齊後端）
      api.articles({ q: dq, limit: 200 }).then(setItems).catch((e) => setErr(String(e.message || e)))
    } else {
      // 無關鍵字：分批載入（可看到全部歷年文章，不再只有最新一批）
      api
        .articles({ limit: PAGE, offset: 0 })
        .then((list) => {
          setItems(list)
          setHasMore(list.length === PAGE)
        })
        .catch((e) => setErr(String(e.message || e)))
    }
  }, [dq])

  const loadMore = useCallback(() => {
    if (loadingMore || !items) return
    setLoadingMore(true)
    api
      .articles({ limit: PAGE, offset: items.length })
      .then((list) => {
        setItems((prev) => [...prev, ...list])
        setHasMore(list.length === PAGE)
      })
      .catch((e) => setErr(String(e.message || e)))
      .finally(() => setLoadingMore(false))
  }, [items, loadingMore])

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
      ) : items.length === 0 ? (
        <p className="muted">{dq ? `找不到含「${dq}」的文章。` : '目前還沒有文章。'}</p>
      ) : (
        <>
          {dq && <p className="muted search-count">找到 {items.length} 篇含「{dq}」的文章</p>}
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
          {!dq && hasMore && (
            <div className="load-more">
              <button className="btn" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? '載入中…' : '載入更多'}
              </button>
            </div>
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
