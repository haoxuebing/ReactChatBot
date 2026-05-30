const EMOJI_ITEM_RE = /([🌡️☁️💧🍃☀️🌙📅⚠️✅❌🔍💡🌧️⛅🌤️❄️🌈]\s*[^：:\n]{1,24}[：:])/g

export function formatAssistantMarkdown(content) {
  if (!content) return ''

  let text = content.replace(/\r\n/g, '\n').trim()

  // 分隔线
  text = text.replace(/\s*---+\s*/g, '\n\n---\n\n')

  // 冒号后的日期标题
  text = text.replace(
    /([：:]\s*)(\d{1,2}月\d{1,2}日[（(][^）)\n]+[）)])/g,
    '$1\n\n### $2\n\n'
  )

  // 日期块标题：5月30日（周六）
  text = text.replace(
    /([。！？；\n])\s*(\d{1,2}月\d{1,2}日[（(][^）)\n]+[）)])/g,
    '$1\n\n### $2\n\n'
  )
  text = text.replace(/^(\d{1,2}月\d{1,2}日[（(][^）)\n]+[）)])/m, '### $1\n\n')

  // 独立日期（无括号）
  text = text.replace(
    /([。！？；\n])\s*(\d{4}年\d{1,2}月\d{1,2}日)/g,
    '$1\n\n### $2\n\n'
  )

  // emoji 标签拆成列表项
  text = text.replace(/([。；！？\n])\s*(?=[🌡️☁️💧🍃☀️🌙📅⚠️✅❌🔍💡🌧️⛅🌤️❄️🌈])/g, '$1\n')
  text = text.replace(EMOJI_ITEM_RE, (match) => {
    return match.startsWith('- ') ? match : `- ${match.trim()}`
  })

  // 「出行建议」「总结」等小节
  text = text.replace(
    /([。！？\n])\s*((?:出行建议|温馨提示|总结|补充说明|数据来源)[：:])/g,
    '$1\n\n**$2**\n\n'
  )
  text = text.replace(/\s+((?:出行建议|温馨提示|总结|补充说明|数据来源)[：:])/g, '\n\n**$1**\n\n')

  // 普通「标签：」拆行（温度、湿度、风力等）
  text = text.replace(
    /([。；！？\n])\s*((?:温度|湿度|风力|风向|天气|降水|紫外线|穿衣|体感)[：:])/g,
    '$1\n- $2'
  )

  // 合并过多空行
  text = text.replace(/\n{3,}/g, '\n\n')

  return text.trim()
}
