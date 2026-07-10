import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 文章由後台（可信）撰寫；仍以 DOMPurify 淨化，避免內容夾帶惡意 HTML。
export default function Markdown({ text }) {
  const html = DOMPurify.sanitize(marked.parse(text || '', { breaks: true }))
  return <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />
}
