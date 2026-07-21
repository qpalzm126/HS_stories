import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api.js'

const PAGE_SIZES = [20, 50, 100, 200]

export default function Dashboard() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [err, setErr] = useState('')
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('') // '' = 全部
  const [sort, setSort] = useState('updated_desc')
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(() => Number(localStorage.getItem('hs_page_size')) || 20)
  const nav = useNavigate()

  const load = useCallback(() => {
    return api
      .adminArticles({ q, status, sort, limit: pageSize, offset: page * pageSize })
      .then((d) => {
        setItems(d.items)
        setTotal(d.total)
      })
      .catch((e) => setErr(String(e.message || e)))
  }, [q, status, sort, page, pageSize])

  // 搜尋/篩選/排序/每頁筆數改變時回到第 1 頁（用 debounce 讓打字不會每個字都打 API）
  useEffect(() => {
    const t = setTimeout(() => setPage(0), 250)
    return () => clearTimeout(t)
  }, [q, status, sort, pageSize])

  useEffect(() => {
    load()
  }, [load])

  async function act(fn) {
    setErr('')
    try {
      await fn()
      await load()
    } catch (e) {
      setErr(String(e.message || e))
    }
  }

  const pages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : page * pageSize + 1
  const to = Math.min(total, (page + 1) * pageSize)

  return (
    <div className="admin">
      <div className="admin-head">
        <h1>文章管理</h1>
        <div className="admin-actions">
          <Link className="btn" to="/admin/ingest">從 LINE 產生</Link>
          <Link className="btn" to="/admin/new">新增文章</Link>
          <a className="btn" href="/" target="_blank" rel="noreferrer">看網站</a>
          <button className="btn" onClick={() => { api.logout(); nav('/admin/login') }}>登出</button>
        </div>
      </div>

      <div className="filters">
        <div className="field grow">
          <label>搜尋標題</label>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="輸入標題關鍵字…" />
        </div>
        <div className="field">
          <label>狀態</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">全部</option>
            <option value="draft">草稿</option>
            <option value="published">已發佈</option>
          </select>
        </div>
        <div className="field">
          <label>排序</label>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="updated_desc">更新時間（新→舊）</option>
            <option value="published_desc">發佈時間（新→舊）</option>
            <option value="published_asc">發佈時間（舊→新）</option>
          </select>
        </div>
        <div className="field">
          <label>每頁筆數</label>
          <select
            value={pageSize}
            onChange={(e) => { const n = Number(e.target.value); setPageSize(n); localStorage.setItem('hs_page_size', String(n)) }}
          >
            {PAGE_SIZES.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
      </div>

      {err && <p className="error">{err}</p>}

      {items.length === 0 ? (
        <p className="muted">{total === 0 && !q && !status ? '還沒有文章。點「從 LINE 產生」或「新增文章」開始。' : '沒有符合條件的文章。'}</p>
      ) : (
        <>
          <table className="tbl">
            <thead>
              <tr><th>標題</th><th>狀態</th><th>發佈</th><th>更新</th><th></th></tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id}>
                  <td>{a.title}</td>
                  <td>{a.status === 'published' ? <span className="pill on">已發佈</span> : <span className="pill">草稿</span>}</td>
                  <td className="muted">{(a.published_at || '').slice(0, 10) || '—'}</td>
                  <td className="muted">{(a.updated_at || '').slice(0, 10)}</td>
                  <td className="row-actions">
                    <Link className="btn sm" to={`/admin/edit/${a.id}`}>編輯</Link>
                    {a.status === 'published' ? (
                      <button className="btn sm" onClick={() => act(() => api.unpublish(a.id))}>取消發佈</button>
                    ) : (
                      <button className="btn sm primary" onClick={() => act(() => api.publish(a.id))}>發佈</button>
                    )}
                    <button
                      className="btn sm danger"
                      onClick={() => { if (window.confirm('確定刪除這篇？')) act(() => api.remove(a.id)) }}
                    >
                      刪除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="pager">
            <span className="muted">第 {from}–{to} 筆，共 {total} 筆</span>
            <div className="pager-btns">
              <button className="btn sm" disabled={page <= 0} onClick={() => setPage((p) => p - 1)}>← 上一頁</button>
              <span className="muted">{page + 1} / {pages}</span>
              <button className="btn sm" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)}>下一頁 →</button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
