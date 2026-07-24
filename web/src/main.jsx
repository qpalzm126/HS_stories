import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './styles.css'

import Home from './pages/Home.jsx'
import Article from './pages/Article.jsx'
import Calendar from './pages/Calendar.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/admin/Dashboard.jsx'
import Editor from './pages/admin/Editor.jsx'
import Ingest from './pages/admin/Ingest.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'

const Protected = ({ children }) => <ProtectedRoute>{children}</ProtectedRoute>
const AdminOnly = ({ children }) => <ProtectedRoute adminOnly>{children}</ProtectedRoute>

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/* /login 是唯一免登入路由 */}
        <Route path="/login" element={<Login />} />

        {/* 公開頁面：整站需登入 */}
        <Route path="/" element={<Protected><Home /></Protected>} />
        <Route path="/calendar" element={<Protected><Calendar /></Protected>} />
        <Route path="/article/:slug" element={<Protected><Article /></Protected>} />

        {/* 後台：需管理員 */}
        <Route path="/admin" element={<AdminOnly><Dashboard /></AdminOnly>} />
        <Route path="/admin/ingest" element={<AdminOnly><Ingest /></AdminOnly>} />
        <Route path="/admin/new" element={<AdminOnly><Editor /></AdminOnly>} />
        <Route path="/admin/edit/:id" element={<AdminOnly><Editor /></AdminOnly>} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
