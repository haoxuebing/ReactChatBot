<template>
  <div v-if="shouldRender" class="flex gap-3 mb-6">
    <div class="flex-shrink-0 w-9 h-9 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white mt-0.5">
      <Bot :size="18" />
    </div>

    <div class="flex-1 min-w-0 max-w-3xl space-y-2">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-sm font-medium text-gray-700">Agent</span>
        <span v-if="timestamp" class="text-xs text-gray-400">{{ formatTime(timestamp) }}</span>
      </div>

      <CollapsibleStep
        v-for="step in message.processSteps"
        :key="step.id"
        :step="step"
      />

      <div v-if="message.isLoading" class="flex items-center gap-2 py-2">
        <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms" />
        <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms" />
        <span class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms" />
      </div>

      <div v-if="displayContent" class="pt-2 text-gray-800">
        <MarkdownRenderer :content="displayContent" class="markdown-content" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bot } from 'lucide-vue-next'
import CollapsibleStep from './CollapsibleStep.vue'
import MarkdownRenderer from './MarkdownRenderer.vue'
import { sanitizeAssistantContent } from '../utils/messageUtils'
import { formatAssistantMarkdown } from '../utils/formatContent'

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
})

const displayContent = computed(() => {
  if (!props.message.assistant?.content) return ''
  const cleaned = sanitizeAssistantContent(props.message.assistant.content)
  return formatAssistantMarkdown(cleaned)
})

const shouldRender = computed(() => {
  return (
    props.message.processSteps?.length > 0
    || props.message.isLoading
    || !!displayContent.value
  )
})

const timestamp = computed(
  () => props.message.assistant?.timestamp || props.message.processSteps?.at(-1)?.timestamp
)

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>
