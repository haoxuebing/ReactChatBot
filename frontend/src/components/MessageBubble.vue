<template>
  <div v-if="shouldRender" class="mb-4">
    <div
      class="flex gap-2 sm:gap-3"
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
        <div v-if="message.role === 'user'" class="text-white whitespace-pre-wrap">
          {{ message.content }}
        </div>

        <MarkdownRenderer
          v-else-if="displayContent"
          :content="displayContent"
          :render-key="markdownRenderKey"
          class="markdown-content"
        />
      </div>
    </div>

    <p
      v-if="displayTime"
      class="text-xs text-gray-400 mt-1.5"
      :class="message.role === 'user' ? 'text-right mr-10 sm:mr-[3.25rem]' : 'ml-10 sm:ml-[3.25rem]'"
    >
      {{ displayTime }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { User, Bot } from 'lucide-vue-next'
import MarkdownRenderer from './MarkdownRenderer.vue'
import { sanitizeAssistantContent } from '../utils/messageUtils'
import { formatAssistantMarkdown } from '../utils/formatContent'
import { formatMessageTime } from '../utils/messageTimestamp'

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  isStreaming: {
    type: Boolean,
    default: false,
  },
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

const displayTime = computed(() => formatMessageTime(props.message.timestamp))

const markdownRenderKey = computed(() => {
  const len = displayContent.value?.length ?? 0
  return props.isStreaming ? `stream-${len}` : `done-${len}-${displayContent.value}`
})
</script>
