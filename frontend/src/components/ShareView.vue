<template>
  <div class="h-dvh flex flex-col bg-gray-100 dark:bg-gray-900 overflow-hidden">
    <header class="h-14 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center px-3 md:px-6 gap-2 md:gap-3 shrink-0">
      <div class="flex items-center gap-2 md:gap-3 min-w-0 flex-1">
        <div class="w-8 h-8 bg-gradient-to-br from-blue-400 to-purple-500 rounded-lg flex items-center justify-center text-white shrink-0">
          <MessageCircle :size="18" />
        </div>
        <div class="min-w-0">
          <h1 class="text-base md:text-lg font-semibold text-gray-800 dark:text-gray-100 truncate">
            {{ sessionName }}
          </h1>
          <p v-if="!loading && !error" class="text-xs text-gray-400 dark:text-gray-500 truncate">
            分享的对话 · 只读
          </p>
        </div>
      </div>
      <ThemeToggle />
      <a
        href="/"
        class="shrink-0 px-3 py-1.5 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
      >
        开始对话
      </a>
    </header>

    <div v-if="loading" class="flex-1 flex items-center justify-center text-gray-400 dark:text-gray-500">
      加载中...
    </div>

    <div v-else-if="error" class="flex-1 flex flex-col items-center justify-center px-4 text-center">
      <p class="text-gray-600 dark:text-gray-300 mb-2">{{ error }}</p>
      <a href="/" class="text-sm text-blue-500 hover:text-blue-600">返回首页</a>
    </div>

    <ChatArea
      v-else
      :messages="messages"
      :is-loading="false"
      readonly
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { MessageCircle } from 'lucide-vue-next'
import ChatArea from './ChatArea.vue'
import ThemeToggle from './ThemeToggle.vue'
import { getSharedSession } from '../services/api'
import { apiMessagesToLocal } from '../utils/sessionUtils'

const props = defineProps({
  sessionId: {
    type: String,
    required: true,
  },
})

const loading = ref(true)
const error = ref('')
const sessionName = ref('分享的对话')
const messages = ref([])

onMounted(async () => {
  try {
    const result = await getSharedSession(props.sessionId)
    const session = result.session
    if (!session?.messages?.length) {
      error.value = '该会话暂无可分享的内容'
      return
    }
    sessionName.value = session.name || '分享的对话'
    messages.value = apiMessagesToLocal(props.sessionId, session.messages)
  } catch (e) {
    error.value = e.message || '加载分享内容失败'
  } finally {
    loading.value = false
  }
})
</script>
