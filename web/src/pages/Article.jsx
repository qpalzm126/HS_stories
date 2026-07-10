import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api.js'
import Markdown from '../components/Markdown.jsx'

export default function Article() {
  const { slug } = useParams()
  const [a, setA] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    setA(null)
    setErr('')
    api.article(slug).then(setA).catch((e) => setErr(String(e.message || e)))
  }, [slug])

  if (err)
    return (
      <div className="site reading">
        <p className="error">{err}</p>
        <Link to="/" className="back">← 回首頁</Link>
      </div>
    )
  if (!a) return <div className="site reading"><p className="muted">載入中…</p></div>

  return (
    <article className="site reading">
      <Link to="/" className="back">← 全部故事</Link>
      <h1>{a.title}</h1>
      <time className="muted">{(a.published_at || '').slice(0, 10)}</time>
      {a.cover_url && <img className="cover" src={a.cover_url} alt="" />}
      <Markdown text={a.body} />
    </article>
  )
}
