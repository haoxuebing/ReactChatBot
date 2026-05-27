const BASE_URL = 'http://localhost:8000/api'

export function chatStream(sessionId, messages, onMessage, onError, onComplete) {
  let isStopped = false
  let controller = new AbortController()

  const fetchPromise = fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId || '',
      messages: messages,
      stream: true,
    }),
    signal: controller.signal
  })

  async function processStream() {
    try {
      const response = await fetchPromise

      if (isStopped) {
        return
      }

      if (!response.ok) {
        const error = await response.json()
        if (!isStopped) onError(error.detail || '请求失败')
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      try {
        while (!isStopped) {
          const { done, value } = await reader.read()
          
          if (done || isStopped) {
            await reader.cancel()
            break
          }

          buffer += decoder.decode(value, { stream: true })
          
          const lines = buffer.split('\n')
          buffer = lines.pop()

          for (const line of lines) {
            if (isStopped) break
            
            const trimmed = line.trim()
            if (!trimmed) continue
            if (!trimmed.startsWith('data: ')) continue

            const data = trimmed.substring(6)
            if (data === '[DONE]') {
              if (!isStopped) onComplete()
              return
            }

            try {
              const parsed = JSON.parse(data)
              if (!isStopped) onMessage(parsed)
            } catch (e) {
              console.warn('解析消息失败:', e)
            }
          }
        }
        
        if (!isStopped) onComplete()
      } catch (e) {
        if (!isStopped) onError(e.message || '连接中断')
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        // 用户主动停止，不显示错误
      } else if (!isStopped) {
        onError(e.message || '请求失败')
      }
    }
  }

  processStream()

  return {
    stop: () => {
      isStopped = true
      controller.abort()
    }
  }
}

export async function chat(sessionId, messages) {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId || '',
      messages: messages,
      stream: false,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '请求失败')
  }

  return await response.json()
}

export async function getSessions() {
  const response = await fetch(`${BASE_URL}/sessions`)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '获取会话列表失败')
  }

  return await response.json()
}

export async function getSession(sessionId) {
  const response = await fetch(`${BASE_URL}/sessions/${sessionId}`)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '获取会话失败')
  }

  return await response.json()
}

export async function deleteSession(sessionId) {
  const response = await fetch(`${BASE_URL}/sessions/${sessionId}`, {
    method: 'DELETE',
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '删除会话失败')
  }

  return await response.json()
}

export async function getTools() {
  const response = await fetch(`${BASE_URL}/tools`)
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '获取工具列表失败')
  }

  return await response.json()
}
