import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api.js'

export default function Dashboard() {
  const [items, setItems] = useState([])
  const [err, setErr] = useState('')
  const nav = useNavigate()

  const load = () => api.adminArticles().then(setItems).catch((e) => setErr(String(e.message || e)))
  useEffect(() => {
    load()
  }, [])

  async function act(fn) {
    setErr('')
    try {
      await fn()
      load()
    } catch (e) {
      setErr(String(e.message || e))
    }
  }

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

      {err && <p className="error">{err}</p>}

      {items.length === 0 ? (
        <p className="muted">還沒有文章。點「從 LINE 產生」或「新增文章」開始。</p>
      ) : (
        <table className="tbl">
          <thead>
            <tr><th>標題</th><th>狀態</th><th>更新</th><th></th></tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id}>
                <td>{a.title}</td>
                <td>{a.status === 'published' ? <span className="pill on">已發佈</span> : <span className="pill">草稿</span>}</td>
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
      )}
    </div>
  )
}
