import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

export default function Home() {
  const [items, setItems] = useState(null)
  const [err, setErr] = useState('')
  const [q, setQ] = useState('')
  const [dq, setDq] = useState('') // debounced query

  // 打字時 debounce，避免每個字都打 API
  useEffect(() => {
    const t = setTimeout(() => setDq(q.trim()), 250)
    return () => clearTimeout(t)
  }, [q])

  useEffect(() => {
    setItems(null)
    setErr('')
    // 有關鍵字：搜尋（放寬上限抓齊符合的）；無關鍵字：顯示最新 100 篇
    const params = dq ? { q: dq, limit: 500 } : { limit: 100 }
    api.articles(params).then(setItems).catch((e) => setErr(String(e.message || e)))
  }, [dq])

  return (
    <div className="site">
      <header className="site-head">
        <h1>聖靈故事</h1>
        <p className="tagline">見證神的作為</p>
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
        </>
      )}

      <footer className="site-foot">
        <Link to="/admin">後台</Link>
      </footer>
    </div>
  )
}
