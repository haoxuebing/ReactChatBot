<template>
  <div
    v-if="shouldRender"
    class="flex gap-2 sm:gap-3 mb-4"
    :class="[message.role === 'user' ? 'flex-row-reverse' : 'flex-row']"
  >
    <div
      class="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center"
      :class="[
        message.role === 'user'
          ? 'bg-blue-500 text-white'
          : 'bg-gradient-to-br from-blue-400 to-purple-500 text-white'
      ]"
    >
      <User v-if="message.role === 'user'" :size="18" />
      <Bot v-else :size="18" />
    </div>

    <div
      class="max-w-[85%] min-w-0 sm:min-w-[120px] px-3 py-2.5 sm:px-4 sm:py-3 rounded-2xl"
      :class="[
        message.role === 'user'
          ? 'bg-blue-500 text-white rounded-tr-sm'
          : 'bg-gray-100 text-gray-800 rounded-tl-sm'
      ]"
    >
      <div v-if="message.role !== 'user'" class="flex items-center gap-2 mb-2">
        <span class="text-sm font-medium text-gray-600">Agent</span>
        <span class="text-xs text-gray-400">{{ formatTime(message.timestamp) }}</span>
      </div>

      <div v-if="message.role === 'user'" class="text-white whitespace-pre-wrap">
        {{ message.content }}
      </div>

      <MarkdownRenderer
        v-else-if="displayContent"
        :content="displayContent"
        class="markdown-content"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { User, Bot } from 'lucide-vue-next'
import MarkdownRenderer from './MarkdownRenderer.vue'
import { sanitizeAssistantContent } from '../utils/messageUtils'
import { formatAssistantMarkdown } from '../utils/formatContent'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const displayContent = computed(() => {
  if (props.message.role !== 'assistant') return props.message.content
  const cleaned = sanitizeAssistantContent(props.message.content)
  return formatAssistantMarkdown(cleaned)
})

const shouldRender = computed(() => {
  if (props.message.role === 'assistant' && !displayContent.value) return false
  return true
})

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>
