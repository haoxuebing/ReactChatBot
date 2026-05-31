<template>
  <div class="flex-1 flex flex-col h-full bg-white">
    <div v-if="messages.length === 0" class="flex-1 flex flex-col items-center justify-center text-gray-400">
      <div class="w-20 h-20 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white mb-4">
        <Sparkles :size="40" />
      </div>
      <h2 class="text-xl font-semibold text-gray-600 mb-2">有什么可以帮你的？</h2>
      <p class="text-sm text-gray-400">支持联网搜索、计算与日期查询，直接提问即可</p>
    </div>
    
    <div v-else ref="messagesContainer" class="flex-1 overflow-y-auto p-6">
      <template v-for="message in displayMessages" :key="message.id">
        <AgentTurnBubble v-if="message.role === 'agent_turn'" :message="message" />
        <MessageBubble v-else :message="message" />
      </template>
    </div>
    
    <div class="border-t border-gray-200 p-4">
      <div class="max-w-4xl mx-auto">
        <div class="flex items-end gap-3 bg-gray-50 rounded-2xl p-2">
          <button
            @click="$emit('clear-history')"
            class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
            title="清空历史"
          >
            <Trash2 :size="20" />
          </button>
          
          <textarea
            v-model="inputMessage"
            @keydown.enter.exact.prevent="handleSend"
            placeholder="输入消息..."
            class="flex-1 bg-transparent border-none outline-none resize-none px-2 py-2 text-gray-800 placeholder-gray-400"
            rows="1"
            ref="inputRef"
            :disabled="isLoading"
          ></textarea>
          
          <button
            v-if="!isLoading"
            @click="handleSend"
            :disabled="!inputMessage.trim()"
            class="p-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl transition-colors"
            title="发送"
          >
            <Send :size="20" />
          </button>
          <button
            v-else
            @click="$emit('stop-generating')"
            class="p-2.5 bg-red-500 hover:bg-red-600 text-white rounded-xl transition-colors"
            title="停止生成"
          >
            <Square :size="20" />
          </button>
        </div>
        
        <p class="text-xs text-gray-400 mt-2 text-center">
          按 Enter 发送消息
        </p>
        <p class="text-xs text-gray-300 mt-1 text-center">
          © 2026 NiceBing
        </p>
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
