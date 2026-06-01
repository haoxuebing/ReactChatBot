export function getSessionId(session) {
  return session?.id || session?.session_id || null
}

export function normalizeSession(raw) {
  const id = getSessionId(raw)
  return {
    id,
    name: raw.name || '未命名会话',
    lastMessage: raw.last_message || raw.lastMessage || '',
    messageCount: raw.message_count ?? 0,
    createdAt: raw.createdAt || Date.now(),
  }
}

export function apiMessagesToLocal(sessionId, messages = []) {
  return messages.map((m, index) => ({
    id: `${sessionId}-${index}`,
    role: m.role,
    content: m.content,
    timestamp: m.timestamp ?? null,
    ip: m.ip ?? null,
  }))
}

export function deriveSessionMetaFromMessages(messages) {
  const firstUser = messages.find(m => m.role === 'user')
  const lastMsg = [...messages].reverse().find(m => m.role === 'user' || m.role === 'assistant')

  let name = '未命名会话'
  if (firstUser?.content) {
    const content = firstUser.content
    name = content.length > 20 ? `${content.substring(0, 20)}...` : content
  }

  let lastMessage = ''
  if (lastMsg?.content) {
    const content = lastMsg.content
    lastMessage = content.length > 30 ? `${content.substring(0, 30)}...` : content
  }

  return { name, lastMessage }
}
