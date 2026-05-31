export function formatToolStepSummary(toolCall) {
  if (!toolCall) return '工具调用'
  const name = getToolLabel(toolCall.name)
  const args = toolCall.arguments || {}

  if (toolCall.name === 'date_tool') {
    const action = args.action || 'now'
    if (action === 'now') return `${name} · 获取当前时间`
    if (action === 'add') return `${name} · 日期加 ${args.days ?? 0} 天`
    if (action === 'diff') return `${name} · 计算日期差`
    if (action === 'format') return `${name} · 格式化日期`
    return `${name} · ${action}`
  }
  if (toolCall.name === 'web_search') {
    return `${name} · ${args.query || ''}`
  }
  if (toolCall.name === 'weather_tool') {
    const parts = [args.city, args.date].filter(Boolean)
    return `${name} · ${parts.join(' · ') || ''}`
  }
  if (toolCall.name === 'calculator') {
    return `${name} · ${args.expression || args.query || ''}`
  }

  const argText = Object.values(args).filter(Boolean).join(', ')
  return argText ? `${name} · ${argText}` : name
}

export function summarizeToolResult(result) {
  if (!result) return ''
  const oneLine = result.replace(/\s+/g, ' ').trim()
  return oneLine.length > 120 ? `${oneLine.slice(0, 120)}…` : oneLine
}

export function groupMessagesForDisplay(messages, options = {}) {
  const { isLoading = false } = options
  const result = []
  let turn = null

  function flushTurn(isLastTurn = false) {
    if (!turn) return

    result.push(turn.user)

    const hasAssistantContent = turn.assistant
      ? !!sanitizeAssistantContent(turn.assistant.content)
      : false
    const hasProcess = turn.processSteps.length > 0
    const showLoading = isLastTurn && isLoading && !hasAssistantContent

    if (hasProcess || hasAssistantContent || showLoading) {
      result.push({
        id: `turn-${turn.user.id}`,
        role: 'agent_turn',
        processSteps: [...turn.processSteps],
        assistant: hasAssistantContent ? turn.assistant : null,
        isLoading: showLoading,
      })
    }

    turn = null
  }

  for (const msg of messages) {
    if (msg.role === 'user') {
      flushTurn()
      turn = { user: msg, processSteps: [], assistant: null }
      continue
    }

    if (!turn) {
      result.push(msg)
      continue
    }

    if (msg.role === 'thinking') {
      turn.processSteps.push({
        id: msg.id || `thinking-${turn.processSteps.length}`,
        type: 'thinking',
        content: msg.content,
        timestamp: msg.timestamp,
      })
      continue
    }

    if (msg.role === 'tool' && msg.toolCall) {
      turn.processSteps.push({
        id: msg.id || `tool-${turn.processSteps.length}`,
        type: 'tool',
        toolCall: msg.toolCall,
        timestamp: msg.timestamp,
      })
      continue
    }

    if (msg.role === 'assistant') {
      if (!turn.assistant) {
        turn.assistant = { ...msg }
      } else {
        turn.assistant.content = (turn.assistant.content || '') + (msg.content || '')
      }
    }
  }

  flushTurn(true)
  return result
}

const TOOL_CALL_BLOCK_RE = /```(?:json)?\s*\{[\s\S]*?"name"[\s\S]*?"arguments"[\s\S]*?\}\s*```/gi
const TOOL_CALL_JSON_RE = /\{"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[\s\S]*?\}\s*\}/gi
const PARTIAL_TOOL_JSON_RE = /^\s*\{[\s\S]*?(?:"name"|"arguments")[\s\S]*$/
const INCOMPLETE_JSON_RE = /^\s*\{[\s\S]*$/

export function sanitizeAssistantContent(content) {
  if (!content) return ''
  let cleaned = content.replace(TOOL_CALL_BLOCK_RE, '')
  cleaned = cleaned.replace(TOOL_CALL_JSON_RE, '')
  if (PARTIAL_TOOL_JSON_RE.test(cleaned.trim())) {
    cleaned = ''
  } else if (INCOMPLETE_JSON_RE.test(cleaned.trim()) && !/\}\s*$/.test(cleaned.trim())) {
    cleaned = ''
  }
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim()
  return cleaned
}

export function shouldSuppressContentDelta(delta) {
  if (!delta) return true
  const trimmed = delta.trim()
  if (!trimmed) return true
  if (trimmed.startsWith('{') || trimmed.startsWith('```')) return true
  return false
}

export function looksLikeToolCall(content) {
  if (!content) return false
  const trimmed = content.trim()
  if (trimmed.startsWith('{') || trimmed.startsWith('```')) return true
  return TOOL_CALL_BLOCK_RE.test(content) || TOOL_CALL_JSON_RE.test(content)
}

export const TOOL_LABELS = {
  web_search: '网络搜索',
  weather_tool: '天气查询',
  calculator: '计算器',
  date_tool: '日期工具',
}

export function getToolLabel(name) {
  return TOOL_LABELS[name] || name
}

export function stripLeakedToolContent(messages) {
  const last = messages[messages.length - 1]
  if (last?.role === 'assistant') {
    last.content = sanitizeAssistantContent(last.content)
  }
  while (messages.length > 0) {
    const tail = messages[messages.length - 1]
    if (tail.role !== 'assistant') break
    if (sanitizeAssistantContent(tail.content)) break
    messages.pop()
  }
}
