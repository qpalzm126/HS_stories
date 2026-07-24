import { Navigate, useLocation } from 'react-router-dom'
import { api } from '../api.js'

/**
 * 路由守衛：整站需登入才能瀏覽。
 * - 無 token → 導 /login，並記住原本要去的路徑（登入後導回）。
 * - adminOnly：另檢查 is_admin，非管理員 → 導首頁。
 */
export default function ProtectedRoute({ children, adminOnly = false }) {
  const loc = useLocation()
  if (!api.isLoggedIn()) {
    return <Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />
  }
  if (adminOnly && !api.isAdmin()) {
    return <Navigate to="/" replace />
  }
  return children
}
