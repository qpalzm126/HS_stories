import { Link } from 'react-router-dom'
import { api } from '../api.js'

/**
 * 固定浮在畫面右下角的「管理」捷徑，讓管理者在公開頁面隨時可進後台。
 * 只在管理員（is_admin）登入時顯示，一般使用者看不到。
 */
export default function AdminShortcut() {
  if (!api.isAdmin()) return null
  return (
    <Link to="/admin" className="admin-fab" title="管理文章" aria-label="管理文章">
      <span className="admin-fab-icon" aria-hidden="true">⚙</span>
      <span className="admin-fab-text">管理</span>
    </Link>
  )
}
