import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api.js'
import Markdown from '../components/Markdown.jsx'
import AdminShortcut from '../components/AdminShortcut.jsx'

const ttsSupported =
  typeof window !== 'undefined' && 'speechSynthesis' in window

// 把標題 + Markdown 內文整理成適合朗讀的純文字（去標記、換行轉停頓）。
// 對齊 App 版 article_screen.dart 的 _speechText。
function speechText(title, md) {
  const t = (md || '')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '') // 圖片
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // 連結→文字
    .replace(/^\s{0,3}#{1,6}\s*/gm, '') // 標題符號
    .replace(/^\s{0,3}[-*+]\s+/gm, '') // 清單符號
    .replace(/^\s{0,3}>\s?/gm, '') // 引言符號
    .replace(/[*`_]/g, '')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{2,}/g, '。\n') // 段落間停頓
    .trim()
  return `${title}。\n${t}`
}

// 依標點/換行切成短句：長段落一次朗讀會被瀏覽器中斷（Chrome 已知問題），
// 切成多句依序排入佇列較穩定。
function toChunks(text) {
  return text
    .split(/(?<=[。！？!?\n])/)
    .map((s) => s.trim())
    .filter(Boolean)
}

export default function Article() {
  const { slug } = useParams()
  const [a, setA] = useState(null)
  const [err, setErr] = useState('')
  const [speaking, setSpeaking] = useState(false)
  // 每次朗讀遞增；殘留的 utterance handler 以此判斷是否仍為當前這輪。
  const runRef = useRef(0)

  useEffect(() => {
    setA(null)
    setErr('')
    // 換篇時停掉上一篇的朗讀。
    if (ttsSupported) {
      runRef.current++
      window.speechSynthesis.cancel()
    }
    setSpeaking(false)
    api.article(slug).then(setA).catch((e) => setErr(String(e.message || e)))
  }, [slug])

  // 離開頁面時停止朗讀（不在此 setState，避免對已卸載元件更新）。
  useEffect(
    () => () => {
      if (ttsSupported) {
        runRef.current++
        window.speechSynthesis.cancel()
      }
    },
    [],
  )

  function stop() {
    runRef.current++ // 使殘留 handler 失效
    window.speechSynthesis.cancel()
    setSpeaking(false)
  }

  function speak() {
    const parts = toChunks(speechText(a.title, a.body || ''))
    if (!parts.length) return
    window.speechSynthesis.cancel()
    const run = ++runRef.current
    setSpeaking(true)
    parts.forEach((part, i) => {
      const u = new SpeechSynthesisUtterance(part)
      u.lang = 'zh-TW'
      u.rate = 0.95 // 中文放慢一點較清楚
      if (i === parts.length - 1) {
        u.onend = () => {
          if (run === runRef.current) setSpeaking(false)
        }
      }
      u.onerror = () => {
        if (run === runRef.current) setSpeaking(false)
      }
      window.speechSynthesis.speak(u)
    })
  }

  function toggleSpeak() {
    if (speaking) stop()
    else speak()
  }

  if (err)
    return (
      <div className="site reading">
        <p className="error">{err}</p>
        <Link to="/" className="back">← 回首頁</Link>
      </div>
    )
  if (!a) return <div className="site reading"><p className="muted">載入中…</p></div>

  return (
    <article className="site reading">
      <Link to="/" className="back">← 全部故事</Link>
      <h1>{a.title}</h1>
      <time className="muted">{(a.published_at || '').slice(0, 10)}</time>
      {ttsSupported && (
        <div className="reading-tools">
          <button className="btn sm" onClick={toggleSpeak}>
            {speaking ? '⏹ 停止朗讀' : '🔊 朗讀'}
          </button>
        </div>
      )}
      {a.cover_url && <img className="cover" src={a.cover_url} alt="" />}
      <Markdown text={a.body} />
      <AdminShortcut />
    </article>
  )
}
