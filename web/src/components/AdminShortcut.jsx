import { Link } from 'react-router-dom'
import { api } from '../api.js'

/**
 * 固定浮在畫面右下角的「管理」捷徑，讓已登入的管理者在公開頁面隨時可進後台。
 * 只在已登入（localStorage 有 token）時顯示，一般訪客看不到。
 */
export default function AdminShortcut() {
  if (!api.isLoggedIn()) return null
  return (
    <Link to="/admin" className="admin-fab" title="管理文章" aria-label="管理文章">
      <span className="admin-fab-icon" aria-hidden="true">⚙</span>
      <span className="admin-fab-text">管理</span>
    </Link>
  )
}
