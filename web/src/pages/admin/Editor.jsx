import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../../api.js'
import Markdown from '../../components/Markdown.jsx'

export default function Editor() {
  const { id } = useParams()
  const nav = useNavigate()
  const [a, setA] = useState({ title: '', excerpt: '', cover_url: '', body: '' })
  const [status, setStatus] = useState('draft')
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => {
    if (!id) return
    api
      .adminArticle(id)
      .then((d) => {
        setA({ title: d.title || '', excerpt: d.excerpt || '', cover_url: d.cover_url || '', body: d.body || '' })
        setStatus(d.status)
      })
      .catch((e) => setErr(String(e.message || e)))
  }, [id])

  const set = (k, v) => setA((s) => ({ ...s, [k]: v }))

  async function save() {
    setErr('')
    setMsg('')
    try {
      const payload = { ...a, ...(id ? { id: Number(id) } : {}) }
      const saved = await api.saveArticle(payload)
      setMsg('已儲存草稿')
      if (!id) nav(`/admin/edit/${saved.id}`, { replace: true })
      else setStatus(saved.status)
    } catch (e) {
      setErr(String(e.message || e))
    }
  }

  async function publish() {
    setErr('')
    setMsg('')
    try {
      const saved = await api.saveArticle({ ...a, ...(id ? { id: Number(id) } : {}) })
      const p = await api.publish(saved.id)
      setStatus(p.status)
      setMsg('已發佈')
      if (!id) nav(`/admin/edit/${saved.id}`, { replace: true })
    } catch (e) {
      setErr(String(e.message || e))
    }
  }

  return (
    <div className="admin editor">
      <div className="admin-head">
        <Link to="/admin" className="back">← 文章管理</Link>
        <div className="admin-actions">
          <span className="pill">{status === 'published' ? '已發佈' : '草稿'}</span>
          <button className="btn" onClick={save}>儲存草稿</button>
          <button className="btn primary" onClick={publish}>發佈</button>
        </div>
      </div>

      {err && <p className="error">{err}</p>}
      {msg && <p className="ok">{msg}</p>}

      <div className="editor-grid">
        <div className="editor-fields">
          <label>標題</label>
          <input value={a.title} onChange={(e) => set('title', e.target.value)} />
          <label>摘錄（列表與桌面小工具顯示）</label>
          <textarea rows="2" value={a.excerpt} onChange={(e) => set('excerpt', e.target.value)} />
          <label>封面圖網址（選填）</label>
          <input value={a.cover_url} onChange={(e) => set('cover_url', e.target.value)} placeholder="https://…" />
          <label>內文（Markdown）</label>
          <textarea rows="22" value={a.body} onChange={(e) => set('body', e.target.value)} />
        </div>
        <div className="editor-preview">
          <h3 className="muted">預覽</h3>
          <h1>{a.title || '（未命名）'}</h1>
          {a.cover_url && <img className="cover" src={a.cover_url} alt="" />}
          <Markdown text={a.body} />
        </div>
      </div>
    </div>
  )
}
