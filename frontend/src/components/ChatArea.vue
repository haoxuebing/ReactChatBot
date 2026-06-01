<template>
  <div class="flex-1 flex flex-col min-h-0 overflow-hidden bg-white min-w-0">
    <div v-if="messages.length === 0" class="flex-1 min-h-0 flex flex-col items-center justify-center text-gray-400 px-4 overflow-y-auto">
      <div class="w-16 h-16 md:w-20 md:h-20 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white mb-4">
        <Sparkles :size="32" class="md:hidden" />
        <Sparkles :size="40" class="hidden md:block" />
      </div>
      <h2 class="text-lg md:text-xl font-semibold text-gray-600 mb-2 text-center">有什么可以帮你的？</h2>
      <p class="text-sm text-gray-400 text-center">支持联网搜索、计算与日期查询，直接提问即可</p>
    </div>

    <div v-else class="flex-1 flex flex-col min-h-0">
      <div class="shrink-0 z-10 bg-white border-b border-gray-100 px-3 sm:px-4 md:px-6 py-2 sm:py-2.5">
        <p class="text-xs text-gray-400 text-center">
          对话次数：{{ turnCount }}
        </p>
      </div>
      <div
        ref="messagesContainer"
        class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-3 sm:p-4 md:p-6"
      >
        <template v-for="(message, index) in displayMessages" :key="message.id">
          <AgentTurnBubble
            v-if="message.role === 'agent_turn'"
            :message="message"
            :is-streaming="isLoading && index === displayMessages.length - 1"
          />
          <MessageBubble
            v-else
            :message="message"
            :is-streaming="isLoading && index === displayMessages.length - 1"
          />
        </template>
      </div>
    </div>
    
    <div class="shrink-0 border-t border-gray-200 bg-white p-2 sm:p-3 md:p-4 pb-safe">
      <div class="max-w-4xl mx-auto">
        <div class="flex items-end gap-2 sm:gap-3 bg-gray-50 rounded-2xl p-1.5 sm:p-2">
          <button
            @click="$emit('clear-history')"
            class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-lg transition-colors shrink-0"
            title="清空历史"
          >
            <Trash2 :size="18" class="sm:hidden" />
            <Trash2 :size="20" class="hidden sm:block" />
          </button>

          <textarea
            v-model="inputMessage"
            @keydown.enter.exact.prevent="handleSend"
            placeholder="输入消息..."
            class="flex-1 min-w-0 bg-transparent border-none outline-none resize-none px-1 sm:px-2 py-2 text-sm sm:text-base text-gray-800 placeholder-gray-400"
            rows="1"
            ref="inputRef"
            :disabled="isLoading"
          ></textarea>

          <button
            v-if="!isLoading"
            @click="handleSend"
            :disabled="!inputMessage.trim()"
            class="p-2 sm:p-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl transition-colors shrink-0"
            title="发送"
          >
            <Send :size="18" class="sm:hidden" />
            <Send :size="20" class="hidden sm:block" />
          </button>
          <button
            v-else
            @click="$emit('stop-generating')"
            class="p-2 sm:p-2.5 bg-red-500 hover:bg-red-600 text-white rounded-xl transition-colors shrink-0"
            title="停止生成"
          >
            <Square :size="18" class="sm:hidden" />
            <Square :size="20" class="hidden sm:block" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { Send, Trash2, Sparkles, Square } from 'lucide-vue-next'
import MessageBubble from './MessageBubble.vue'
import AgentTurnBubble from './AgentTurnBubble.vue'
import { groupMessagesForDisplay } from '../utils/messageUtils'

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

const displayMessages = computed(() =>
  groupMessagesForDisplay(props.messages, { isLoading: props.isLoading })
)

const turnCount = computed(() =>
  props.messages.filter((m) => m.role === 'user').length
)

const emit = defineEmits(['send-message', 'clear-history', 'stop-generating'])

const inputMessage = ref('')
const messagesContainer = ref(null)
const inputRef = ref(null)

watch(
  () => [displayMessages.value.length, props.isLoading, props.messages.at(-1)?.content],
  async () => {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  }
)

function handleSend() {
  const content = inputMessage.value.trim()
  if (!content || props.isLoading) return
  emit('send-message', content)
  inputMessage.value = ''
}
</script>
