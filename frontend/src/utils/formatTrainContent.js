const TRAIN_NO_RE = '[GDCZTKXYL]\\d{1,4}'
const TRAIN_CONTEXT_RE =
  /车次|高铁|动车|火车票|余票|出发站|到达站|一等座|二等座|商务座|特等座|无座/
const PIPE_TRAIN_ROW_RE = new RegExp(
  `^\\|\\s*(${TRAIN_NO_RE})\\s*\\|(.+)\\|\\s*$`
)
const RAW_TRAIN_ROW_RE = new RegExp(
  `^(${TRAIN_NO_RE})\\s+(.+?)\\s+(\\d{1,2}:\\d{2})\\s*->\\s*(\\d{1,2}:\\d{2})\\s+历时[：:]\\s*(.+)$`
)
const SEAT_LINE_RE = /^-\s*(商务座|一等座|二等座|特等座|无座|优选一等座)[：:]\s*(.+)$/

function isJunkTableLine(line) {
  const trimmed = line.trim()
  if (!/^\|/.test(trimmed)) return false
  if (new RegExp(`\\b${TRAIN_NO_RE}\\b`).test(trimmed)) return false
  if (/车次/.test(trimmed)) return true
  const cells = trimmed.split('|').map((c) => c.trim()).filter(Boolean)
  return cells.length > 0 && cells.every((c) => /^[-:\s]+$/.test(c))
}

export function isTrainTicketContent(text) {
  if (!text) return false
  const hasTrainNo = new RegExp(`(?:^|\\s|\\|)(${TRAIN_NO_RE})(?:\\s|\\|)`, 'm').test(
    text
  )
  return hasTrainNo && TRAIN_CONTEXT_RE.test(text)
}

function normalizeRoute(route) {
  return route
    .replace(/\(telecode:[A-Z]{3}\)/gi, '')
    .replace(/\s*->\s*/g, ' → ')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

function normalizeDuration(duration) {
  const value = (duration || '').trim()
  if (!value) return ''
  if (/小时|分/.test(value)) return value
  const m = value.match(/^(\d{1,2}):(\d{2})$/)
  if (m) {
    const hours = Number(m[1])
    const mins = Number(m[2])
    if (hours && mins) return `${hours}小时${mins}分`
    if (hours) return `${hours}小时`
    return `${mins}分`
  }
  return value
}

function formatSeatSummary(seats) {
  if (!seats.length) return ''
  return seats
    .map((s) => s.replace(/\s*¥/g, ' ¥').trim())
    .filter(Boolean)
    .join(' · ')
}

function buildTrainCard({ trainNo, route, depart, arrive, duration, seats }) {
  const timeText = `${depart} → ${arrive}`
  const durationText = duration ? `（${normalizeDuration(duration)}）` : ''
  const seatText = formatSeatSummary(seats)
  const lines = [`> **${trainNo}** · ${normalizeRoute(route)}`, `> - 时间：${timeText}${durationText}`]
  if (seatText) {
    lines.push(`> - 票价：${seatText}`)
  }
  return lines.join('\n')
}

function parsePipeTrainRow(line) {
  const match = line.match(PIPE_TRAIN_ROW_RE)
  if (!match) return null

  const parts = match[2].split('|').map((s) => s.trim()).filter(Boolean)
  if (!parts.length) return null

  const route = parts[0] || ''
  const timePart = parts[1] || ''
  const duration = parts[2] || ''
  const seatLabels = ['二等座', '一等座', '商务座', '无座']
  const seats = parts.slice(3).map((seat, index) => {
    if (/座|无座/.test(seat)) return seat
    const label = seatLabels[index] || `席别${index + 1}`
    return `${label} ${seat}`
  })

  const timeMatch = timePart.match(/(\d{1,2}:\d{2})\s*[-–—→]\s*(\d{1,2}:\d{2})/)
  const depart = timeMatch?.[1] || timePart
  const arrive = timeMatch?.[2] || ''

  return buildTrainCard({
    trainNo: match[1],
    route,
    depart,
    arrive,
    duration,
    seats,
  })
}

function parseRawTrainBlock(lines, startIndex) {
  const first = lines[startIndex]
  const match = first.match(RAW_TRAIN_ROW_RE)
  if (!match) return null

  const seats = []
  let cursor = startIndex + 1
  while (cursor < lines.length) {
    const line = lines[cursor].trim()
    if (!line) break
    const seatMatch = line.match(SEAT_LINE_RE)
    if (!seatMatch) break
    seats.push(`${seatMatch[1]} ${seatMatch[2].trim()}`)
    cursor += 1
  }

  const route = match[2]
  return {
    card: buildTrainCard({
      trainNo: match[1],
      route,
      depart: match[3],
      arrive: match[4],
      duration: match[5],
      seats,
    }),
    nextIndex: cursor,
  }
}

function promoteSectionHeader(line) {
  const trimmed = line.trim()
  const sectionMatch = trimmed.match(
    /^[-*]?\s*([🌅🌞🌙☀️🌆🚄🚆]\s*.+)$/
  )
  if (sectionMatch) {
    return `### ${sectionMatch[1].trim()}`
  }
  if (/^#{1,3}\s+[🌅🌞🌙☀️🌆🚄🚆]/.test(trimmed)) {
    return trimmed.replace(/^#{1,3}\s+/, '### ')
  }
  return null
}

function isSummaryLine(line) {
  return /温馨提示|出行建议|推荐|总结|💡/.test(line)
}

export function formatTrainTicketMarkdown(content) {
  if (!content || !isTrainTicketContent(content)) return content

  const lines = content.replace(/\r\n/g, '\n').split('\n')
  const output = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]
    const trimmed = line.trim()

    if (!trimmed) {
      if (output.length && output[output.length - 1] !== '') {
        output.push('')
      }
      index += 1
      continue
    }

    if (isJunkTableLine(trimmed) || /^\|\s*:+\s*\|?$/.test(trimmed)) {
      index += 1
      continue
    }

    const section = promoteSectionHeader(trimmed)
    if (section) {
      output.push('', section, '')
      index += 1
      continue
    }

    const pipeCard = parsePipeTrainRow(trimmed)
    if (pipeCard) {
      output.push(pipeCard, '')
      index += 1
      continue
    }

    const rawBlock = parseRawTrainBlock(lines, index)
    if (rawBlock) {
      output.push(rawBlock.card, '')
      index = rawBlock.nextIndex
      continue
    }

    if (isSummaryLine(trimmed)) {
      const cleaned = trimmed.replace(/^[-*]\s*/, '').trim()
      output.push('', `**${cleaned}**`, '')
      index += 1
      continue
    }

    output.push(line)
    index += 1
  }

  return output.join('\n').replace(/\n{3,}/g, '\n\n').trim()
}
