import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

// ISO 時間 → 本地 YYYY-MM-DD（日曆以本地日期分格）
function localKey(iso) {
  const d = new Date(iso)
  if (isNaN(d)) return ''
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

export default function Calendar() {
  const [items, setItems] = useState(null)
  const [err, setErr] = useState('')
  const [cursor, setCursor] = useState(null) // { year, month }（month 0 起）

  useEffect(() => {
    api
      .articles({ limit: 200 })
      .then((list) => {
        setItems(list)
        // 預設顯示最新一篇所在月份（沒有文章則本月）
        const base = list[0] ? new Date(list[0].published_at) : new Date()
        setCursor({ year: base.getFullYear(), month: base.getMonth() })
      })
      .catch((e) => setErr(String(e.message || e)))
  }, [])

  // 依本地日期把文章分組
  const byDate = useMemo(() => {
    const map = new Map()
    for (const a of items || []) {
      const k = localKey(a.published_at)
      if (!k) continue
      if (!map.has(k)) map.set(k, [])
      map.get(k).push(a)
    }
    return map
  }, [items])

  if (err)
    return (
      <div className="site">
        <p className="error">{err}</p>
        <Link to="/" className="back">← 回首頁</Link>
      </div>
    )
  if (!items || !cursor) return <div className="site"><p className="muted">載入中…</p></div>

  const { year, month } = cursor
  const startWeekday = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const todayKey = localKey(new Date().toISOString())

  const cells = []
  for (let i = 0; i < startWeekday; i++) cells.push(null) // 月初補空格
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  while (cells.length % 7 !== 0) cells.push(null)

  const step = (delta) =>
    setCursor(({ year, month }) => {
      const m = month + delta
      if (m < 0) return { year: year - 1, month: 11 }
      if (m > 11) return { year: year + 1, month: 0 }
      return { year, month: m }
    })

  return (
    <div className="site">
      <header className="site-head">
        <h1>聖靈故事日曆</h1>
        <p className="tagline">依日期瀏覽每日的故事</p>
      </header>

      <div className="cal-nav">
        <button className="btn sm" onClick={() => step(-1)}>← 上個月</button>
        <div className="cal-title">{year} 年 {month + 1} 月</div>
        <button className="btn sm" onClick={() => step(1)}>下個月 →</button>
      </div>

      <div className="cal-grid">
        {WEEKDAYS.map((w) => (
          <div key={w} className="cal-wd">{w}</div>
        ))}
        {cells.map((d, i) => {
          if (d === null) return <div key={i} className="cal-cell empty" />
          const key = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
          const stories = byDate.get(key) || []
          const cls =
            'cal-cell' + (stories.length ? ' has' : '') + (key === todayKey ? ' today' : '')
          return (
            <div key={i} className={cls}>
              <div className="cal-day">{d}</div>
              {stories.map((s) => (
                <Link key={s.slug} className="cal-story" to={`/article/${s.slug}`} title={s.title}>
                  {s.title}
                </Link>
              ))}
            </div>
          )
        })}
      </div>

      <footer className="site-foot">
        <Link to="/">← 回全部故事</Link>
      </footer>
    </div>
  )
}
