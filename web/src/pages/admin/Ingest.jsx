import { useEffect, useRef, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../../api.js'

export default function Ingest() {
  const nav = useNavigate()
  const fileRef = useRef(null)
  const [convs, setConvs] = useState([])
  const [senders, setSenders] = useState([])
  const [f, setF] = useState({ conversation: '', sender: '', q: '', date_from: '', date_to: '' })
  const [messages, setMessages] = useState(null)
  const [selected, setSelected] = useState(new Set())
  const [instructions, setInstructions] = useState('')
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  const [note, setNote] = useState('')

  useEffect(() => {
    api.conversations().then(setConvs).catch(() => {})
  }, [])
  useEffect(() => {
    api.senders(f.conversation).then(setSenders).catch(() => setSenders([]))
  }, [f.conversation])

  const set = (k, v) => setF((s) => ({ ...s, [k]: v }))

  function withTime() {
    const x = { ...f }
    if (x.date_from) x.date_from = `${x.date_from}T00:00:00`
    if (x.date_to) x.date_to = `${x.date_to}T23:59:59`
    return x
  }

  async function upload(e) {
    const file = e.target.files[0]
    if (!file) return
    setErr('')
    setBusy('upload')
    try {
      const r = await api.importFile(file)
      setNote(`已匯入「${r.conversation}」：新增 ${r.added}、略過 ${r.skipped}`)
      api.conversations().then(setConvs)
    } catch (e) {
      setErr(String(e.message || e))
    } finally {
      setBusy('')
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function search() {
    setErr('')
    setBusy('search')
    try {
      const r = await api.messages({ ...withTime(), limit: 500 })
      setMessages(r.messages)
      setSelected(new Set())
    } catch (e) {
      setErr(String(e.message || e))
    } finally {
      setBusy('')
    }
  }

  function toggle(mid) {
    setSelected((s) => {
      const n = new Set(s)
      n.has(mid) ? n.delete(mid) : n.add(mid)
      return n
    })
  }
  const selectAll = () => setSelected(new Set((messages || []).map((m) => m.id)))
  const clearSel = () => setSelected(new Set())

  async function generate() {
    setErr('')
    const count = selected.size > 0 ? selected.size : (messages ? messages.length : 0)
    if (count === 0) {
      setErr('請先搜尋並（可選）勾選要用的訊息。')
      return
    }
    if (!window.confirm(`將把 ${count} 則訊息送到 Claude API 產生文章草稿，是否繼續？`)) return
    setBusy('draft')
    try {
      const payload =
        selected.size > 0
          ? { message_ids: [...selected], instructions }
          : { ...withTime(), instructions }
      const r = await api.draft(payload)
      const d = r.draft
      const saved = await api.saveArticle({
        title: d.title,
        excerpt: d.excerpt,
        body: d.body_markdown,
        source_ref: JSON.stringify(payload).slice(0, 500),
      })
      nav(`/admin/edit/${saved.id}`)
    } catch (e) {
      setErr(String(e.message || e))
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="admin">
      <div className="admin-head">
        <Link to="/admin" className="back">← 文章管理</Link>
        <h1>從 LINE 產生文章</h1>
      </div>

      <div className="ingest-step">
        <b>1. 匯入 LINE 匯出檔</b>
        <label className="btn">
          {busy === 'upload' ? '匯入中…' : '選擇 .txt'}
          <input ref={fileRef} type="file" accept=".txt" hidden onChange={upload} />
        </label>
        {note && <span className="ok">{note}</span>}
      </div>

      <div className="ingest-step">
        <b>2. 搜尋、勾選要用的訊息</b>
      </div>
      <div className="filters">
        <div className="field">
          <label>對話</label>
          <select value={f.conversation} onChange={(e) => set('conversation', e.target.value)}>
            <option value="">全部</option>
            {convs.map((c) => (
              <option key={c.conversation} value={c.conversation}>{c.conversation}（{c.count}）</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>發送者</label>
          <select value={f.sender} onChange={(e) => set('sender', e.target.value)}>
            <option value="">全部</option>
            {senders.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div className="field grow">
          <label>關鍵字</label>
          <input value={f.q} onChange={(e) => set('q', e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} />
        </div>
        <div className="field">
          <label>起</label>
          <input type="date" value={f.date_from} onChange={(e) => set('date_from', e.target.value)} />
        </div>
        <div className="field">
          <label>迄</label>
          <input type="date" value={f.date_to} onChange={(e) => set('date_to', e.target.value)} />
        </div>
        <button className="btn" disabled={!!busy} onClick={search}>{busy === 'search' ? '搜尋中…' : '搜尋'}</button>
      </div>

      {err && <p className="error">{err}</p>}

      {messages && (
        <div className="msg-select">
          <div className="msg-select-bar">
            <span className="muted">共 {messages.length} 則，已選 {selected.size} 則</span>
            <button className="btn sm" onClick={selectAll}>全選</button>
            <button className="btn sm" onClick={clearSel}>清除</button>
          </div>
          <div className="msg-list">
            {messages.length === 0 && <p className="muted">沒有符合的訊息。</p>}
            {messages.map((m) => (
              <label className={`msg-row ${selected.has(m.id) ? 'sel' : ''}`} key={m.id}>
                <input type="checkbox" checked={selected.has(m.id)} onChange={() => toggle(m.id)} />
                <span className="meta"><b>{m.sender}</b> · {m.sent_at}</span>
                <span className="body">{m.content}</span>
              </label>
            ))}
          </div>
          <p className="muted small">不勾選則使用目前搜尋條件的全部訊息。</p>
        </div>
      )}

      <div className="ingest-step">
        <b>3. 產生草稿</b>
      </div>
      <div className="draft-gen">
        <input
          placeholder="給 Claude 的額外指示（選填），例如：以第一人稱、加上經文出處"
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
        />
        <button className="btn primary" disabled={!!busy} onClick={generate}>
          {busy === 'draft' ? 'Claude 產生中…' : '產生文章草稿'}
        </button>
      </div>
    </div>
  )
}
