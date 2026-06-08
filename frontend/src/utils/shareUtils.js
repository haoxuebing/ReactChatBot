export function buildShareUrl(sessionId) {
  if (!sessionId) return ''
  const base = window.location.origin
  return `${base}/share/${encodeURIComponent(sessionId)}`
}

export async function copyShareLink(sessionId) {
  const url = buildShareUrl(sessionId)
  if (!url) throw new Error('无效的会话 ID')

  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(url)
    return url
  }

  const textarea = document.createElement('textarea')
  textarea.value = url
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
  return url
}
