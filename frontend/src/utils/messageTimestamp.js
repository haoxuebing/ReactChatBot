const DATETIME_RE = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/

/** 生成 YYYY-MM-DD HH:mm:ss 格式时间戳 */
export function messageTimestamp(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

/** 展示消息时间（兼容历史毫秒时间戳） */
export function formatMessageTime(timestamp) {
  if (!timestamp) return ''
  if (typeof timestamp === 'string' && DATETIME_RE.test(timestamp)) {
    return timestamp
  }
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return String(timestamp)
  return messageTimestamp(date)
}
