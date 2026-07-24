import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api.js'

const SERVERS = [
  { value: 'heavensbride', label: 'HeavensBride' },
  { value: 'tcgm', label: 'TCGM' },
]

export default function Login() {
  const [server, setServer] = useState('heavensbride')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()
  const loc = useLocation()
  const from = loc.state?.from || '/'

  async function submit(e) {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try {
      await api.login({ server, username: username.trim(), password })
      nav(from, { replace: true })
    } catch (e) {
      setErr(String(e.message || e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="site">
      <form className="login" onSubmit={submit}>
        <h1>登入聖靈故事</h1>
        <p className="muted login-hint">請用論壇帳密登入</p>

        <div className="login-servers" role="radiogroup" aria-label="登入來源">
          {SERVERS.map((s) => (
            <label key={s.value} className={'login-server' + (server === s.value ? ' active' : '')}>
              <input
                type="radio"
                name="server"
                value={s.value}
                checked={server === s.value}
                onChange={() => setServer(s.value)}
              />
              {s.label}
            </label>
          ))}
        </div>

        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="帳號"
          autoComplete="username"
          autoFocus
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="密碼"
          autoComplete="current-password"
        />
        <button className="btn primary" type="submit" disabled={busy || !username || !password}>
          {busy ? '登入中…' : '登入'}
        </button>
        {err && <p className="error">{err}</p>}
      </form>
    </div>
  )
}
