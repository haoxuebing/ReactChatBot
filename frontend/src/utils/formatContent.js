const EMOJI_ITEM_RE = /([🌡️☁️💧🍃☀️🌙📅⚠️✅❌🔍💡🌧️⛅🌤️❄️🌈]\s*[^：:\n]{1,24}[：:])/g

const WEATHER_METRICS =
  '天气|温度|风力|风向|湿度|降水量|降水|紫外线指数|体感|能见度|云量|气压|白天|夜间'

const WEATHER_METRIC_SPLIT_RE = new RegExp(
  `([^\\n-])(?=(${WEATHER_METRICS})[：:])`,
  'g'
)

const WEATHER_METRIC_LINE_RE = new RegExp(
  `^(\\s*)((?:${WEATHER_METRICS})[：:])`,
  'gm'
)

const ISO_DATE_TITLE_RE =
  /(\d{4}-\d{2}-\d{2})(?:[（(]([^）)\n]+)[）)])?/g

const CODE_BLOCK_PLACEHOLDER = (index) => `\x00CODEBLOCK${index}\x00`

function preserveCodeBlocks(text, transform) {
  const blocks = []
  const stripped = text.replace(/```[\s\S]*?```/g, (block) => {
    const index = blocks.length
    blocks.push(block)
    return CODE_BLOCK_PLACEHOLDER(index)
  })

  let result = transform(stripped)
  blocks.forEach((block, index) => {
    result = result.replace(CODE_BLOCK_PLACEHOLDER(index), () => block)
  })
  return result
}

function splitInlineHeaders(text) {
  let result = text.replace(/(^|\n)(#{1,3})([^\s#\n])/gm, '$1$2 $3')
  result = result.replace(/\s*#{1,3}\s+/g, (match) => {
    const level = (match.match(/#/g) || []).length
    return `\n\n${'#'.repeat(level)} `
  })
  return result
}

function promoteDateTitles(text) {
  let result = text.replace(
    /([。：；！？\n]|^)\s*(\d{4}-\d{2}-\d{2}[（(][^）)\n]+[）)])/g,
    '$1\n\n### $2\n\n'
  )
  result = result.replace(
    /([。：；！？\n]|^)\s*(\d{4}-\d{2}-\d{2})(?![（(\d])/g,
    '$1\n\n### $2\n\n'
  )
  return result
}

function splitWeatherMetrics(text) {
  // 已是列表项或指标已加粗时不再拆分，避免破坏 **天气**： 等 Markdown
  const listMetricRe = new RegExp(`^-\\s+\\*{0,2}(?:${WEATHER_METRICS})`, 'm')
  if (listMetricRe.test(text)) {
    return text
  }

  const safeSplitRe = new RegExp(
    `([^\\n-*])(?=(${WEATHER_METRICS})[：:])`,
    'g'
  )
  let result = text.replace(safeSplitRe, '$1\n- ')
  result = result.replace(WEATHER_METRIC_LINE_RE, '$1- $2')
  return result
}

const SUMMARY_LABELS =
  '总体趋势|出行建议|温馨提示|总结|补充说明|数据来源'

const SUMMARY_LABELS_RE = new RegExp(SUMMARY_LABELS)

function formatSummarySections(text) {
  if (new RegExp(`\\*\\*(?:${SUMMARY_LABELS})[：:]`).test(text)) {
    return text
  }
  return text.replace(
    new RegExp(`(?<!\\*)\\s*((?:${SUMMARY_LABELS}))[：:](?!\\*)`, 'g'),
    '\n\n**$1：**\n\n'
  )
}

function normalizeBoldSections(text) {
  let result = text

  // 总体趋势：** → **总体趋势：**
  result = result.replace(
    new RegExp(`(?:^|\\n)\\s*((${SUMMARY_LABELS}))[：:]\\s*\\*\\*`, 'g'),
    '\n\n**$1：**\n\n'
  )

  // **总体趋势：** 后紧跟多余的 ** 行或 ** 开头
  result = result.replace(
    new RegExp(
      `(\\*\\*(?:${SUMMARY_LABELS})[：:]\\*\\*)\\s*\\n+\\s*\\*\\*\\s*\\n`,
      'g'
    ),
    '$1\n\n'
  )
  result = result.replace(
    new RegExp(
      `(\\*\\*(?:${SUMMARY_LABELS})[：:]\\*\\*)\\s*\\n+\\s*\\*\\*\\s+`,
      'g'
    ),
    '$1\n\n'
  )

  // 纯文本「总体趋势：」标题补全加粗
  result = result.replace(
    new RegExp(`(?:^|\\n)\\s*((${SUMMARY_LABELS}))[：:]\\s*\\n(?!\\*\\*)`, 'g'),
    '\n\n**$1：**\n\n'
  )

  return result
}

function cleanupOrphanMarkdown(text) {
  let result = normalizeBoldSections(text)

  // 单独一行的 **
  result = result.replace(/^\s*\*\*\s*$/gm, '')

  // 行首 ** 后接空格但本行无闭合 **（破损的开标记）
  result = result.replace(/^(\s*)\*\*\s+(?=[^\s*].*$)/gm, '$1')

  return result.replace(/\n{3,}/g, '\n\n')
}

function formatIsoDateRangeIntro(text) {
  return text.replace(
    /([：:]\s*)(（覆盖[^）\n]+）)/g,
    '$1\n\n$2\n\n'
  )
}

function isWellFormattedWeatherMarkdown(text) {
  return /^###\s+\d{4}-\d{2}-\d{2}/m.test(text) && /^-\s+/m.test(text)
}

export function formatAssistantMarkdown(content) {
  if (!content) return ''

  const normalized = content.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim()

  // 含代码块的内容不做天气/标题类二次格式化，避免破坏代码结构
  if (/```/.test(normalized)) {
    return normalized
  }

  // 模型已按规范输出 Markdown 列表时，跳过二次拆分
  if (isWellFormattedWeatherMarkdown(normalized)) {
    return cleanupOrphanMarkdown(normalized)
  }

  return preserveCodeBlocks(normalized, (text) => {
    text = text.replace(/\s*---+\s*/g, '\n\n---\n\n')

    text = splitInlineHeaders(text)
    text = promoteDateTitles(text)
    text = formatIsoDateRangeIntro(text)

    text = text.replace(
      /([：:]\s*)(\d{1,2}月\d{1,2}日[（(][^）)\n]+[）)])/g,
      '$1\n\n### $2\n\n'
    )
    text = text.replace(
      /([。！？；\n])\s*(\d{1,2}月\d{1,2}日[（(][^）)\n]+[）)])/g,
      '$1\n\n### $2\n\n'
    )
    text = text.replace(/^(\d{1,2}月\d{1,2}日[（(][^）)\n]+[）)])/m, '### $1\n\n')

    text = text.replace(
      /([。！？；\n])\s*(\d{4}年\d{1,2}月\d{1,2}日)/g,
      '$1\n\n### $2\n\n'
    )

    text = splitWeatherMetrics(text)
    text = formatSummarySections(text)

    text = text.replace(/([。；！？\n])\s*(?=[🌡️☁️💧🍃☀️🌙📅⚠️✅❌🔍💡🌧️⛅🌤️❄️🌈])/g, '$1\n')
    text = text.replace(EMOJI_ITEM_RE, (match) => {
      return match.startsWith('- ') ? match : `- ${match.trim()}`
    })

    text = text.replace(
      new RegExp(`([。！？\\n])(?<!\\*)\\s*((?:${SUMMARY_LABELS})[：:])(?!\\*)`, 'g'),
      '$1\n\n**$2**\n\n'
    )
    text = text.replace(
      new RegExp(`(?<!\\*)\\s+((?:${SUMMARY_LABELS})[：:])(?!\\*)`, 'g'),
      '\n\n**$1**\n\n'
    )

    return cleanupOrphanMarkdown(text).trim()
  })
}

/** @internal test helper */
export function _formatIsoDateTitle(isoDate, label) {
  return label ? `### ${isoDate}（${label}）` : `### ${isoDate}`
}

export { ISO_DATE_TITLE_RE }
