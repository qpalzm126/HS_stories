import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

export default function Home() {
  const [items, setItems] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.articles(100).then(setItems).catch((e) => setErr(String(e.message || e)))
  }, [])

  return (
    <div className="site">
      <header className="site-head">
        <h1>聖靈故事</h1>
        <p className="tagline">見證神的作為</p>
      </header>

      {err && <p className="error">{err}</p>}

      {items === null ? (
        <p className="muted">載入中…</p>
      ) : items.length === 0 ? (
        <p className="muted">目前還沒有文章。</p>
      ) : (
        <div className="cards">
          {items.map((a) => (
            <Link className="card" to={`/article/${a.slug}`} key={a.slug}>
              {a.cover_url && <img src={a.cover_url} alt="" loading="lazy" />}
              <div className="card-body">
                <h2>{a.title}</h2>
                <p>{a.excerpt}</p>
                <time className="muted">{(a.published_at || '').slice(0, 10)}</time>
              </div>
            </Link>
          ))}
        </div>
      )}

      <footer className="site-foot">
        <Link to="/admin">後台</Link>
      </footer>
    </div>
  )
}
