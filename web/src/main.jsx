import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './styles.css'

import Home from './pages/Home.jsx'
import Article from './pages/Article.jsx'
import Calendar from './pages/Calendar.jsx'
import Login from './pages/admin/Login.jsx'
import Dashboard from './pages/admin/Dashboard.jsx'
import Editor from './pages/admin/Editor.jsx'
import Ingest from './pages/admin/Ingest.jsx'
import { api } from './api.js'

function RequireAuth({ children }) {
  return api.isLoggedIn() ? children : <Navigate to="/admin/login" replace />
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/calendar" element={<Calendar />} />
        <Route path="/article/:slug" element={<Article />} />
        <Route path="/admin/login" element={<Login />} />
        <Route path="/admin" element={<RequireAuth><Dashboard /></RequireAuth>} />
        <Route path="/admin/ingest" element={<RequireAuth><Ingest /></RequireAuth>} />
        <Route path="/admin/new" element={<RequireAuth><Editor /></RequireAuth>} />
        <Route path="/admin/edit/:id" element={<RequireAuth><Editor /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
