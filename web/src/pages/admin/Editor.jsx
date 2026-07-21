import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../../api.js'
import Markdown from '../../components/Markdown.jsx'

// ISO（如 2026-07-21T00:00:00[.…+00:00]）↔ datetime-local（YYYY-MM-DDTHH:MM）互轉。
const toLocal = (iso) => (iso ? String(iso).slice(0, 16) : '')
const toIso = (local) => (local ? (local.length === 16 ? `${local}:00` : local) : undefined)

// 草稿尚未發佈時，發佈時間會落在 source_ref.orig_date（貼上內容夾帶的原始日期）。
function origDateOf(sourceRef) {
  try {
    return (JSON.parse(sourceRef || '{}') || {}).orig_date || ''
  } catch {
    return ''
  }
}

export default function Editor() {
  const { id } = useParams()
  const nav = useNavigate()
  const [a, setA] = useState({ title: '', excerpt: '', cover_url: '', body: '' })
  const [status, setStatus] = useState('draft')
  const [publishedAt, setPublishedAt] = useState('') // datetime-local 字串
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => {
    if (!id) return
    api
      .adminArticle(id)
      .then((d) => {
        setA({ title: d.title || '', excerpt: d.excerpt || '', cover_url: d.cover_url || '', body: d.body || '' })
        setStatus(d.status)
        setPublishedAt(toLocal(d.published_at || origDateOf(d.source_ref)))
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
    const wasPublished = status === 'published'
    try {
      const saved = await api.saveArticle({ ...a, ...(id ? { id: Number(id) } : {}) })
      const p = await api.publish(saved.id, toIso(publishedAt))
      setStatus(p.status)
      setPublishedAt(toLocal(p.published_at))
      setMsg(wasPublished ? '已更新發佈時間' : '已發佈')
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
          <button className="btn primary" onClick={publish}>{status === 'published' ? '更新發佈時間' : '發佈'}</button>
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
          <label>發佈時間（留空則用內容夾帶日期或現在時間；改後按{status === 'published' ? '「更新發佈時間」' : '「發佈」'}生效）</label>
          <input type="datetime-local" value={publishedAt} onChange={(e) => setPublishedAt(e.target.value)} />
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
