import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api.js'

export default function Login() {
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const nav = useNavigate()

  async function submit(e) {
    e.preventDefault()
    setErr('')
    try {
      await api.login(pw)
      nav('/admin')
    } catch (e) {
      setErr(String(e.message || e))
    }
  }

  return (
    <div className="admin">
      <form className="login" onSubmit={submit}>
        <h1>後台登入</h1>
        <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="密碼" autoFocus />
        <button className="btn primary" type="submit">登入</button>
        {err && <p className="error">{err}</p>}
      </form>
    </div>
  )
}
