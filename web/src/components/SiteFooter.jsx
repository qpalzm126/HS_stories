import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api.js'

/**
 * 公開頁面頁尾：一般使用者可登出；管理員另有「後台」入口。
 */
export default function SiteFooter() {
  const nav = useNavigate()
  const user = api.currentUser()

  function logout() {
    api.logout()
    nav('/login')
  }

  return (
    <footer className="site-foot">
      {user && <span className="foot-user">{user.username}</span>}
      {api.isAdmin() && <Link to="/admin">後台</Link>}
      <button type="button" className="link-btn" onClick={logout}>登出</button>
    </footer>
  )
}
