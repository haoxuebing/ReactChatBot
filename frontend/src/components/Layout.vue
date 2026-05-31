<template>
  <div class="h-screen flex bg-gray-100">
    <div
      class="flex flex-col transition-all duration-300 relative"
      :class="[
        sidebarCollapsed ? 'w-12' : 'w-72'
      ]"
    >
      <Sidebar
        v-if="!sidebarCollapsed"
        :sessions="sessions"
        :current-session-id="currentSessionId"
        :collapsed="sidebarCollapsed"
        :username="username"
        @new-session="handleNewSession"
        @select-session="handleSelectSession"
        @delete-session="handleDeleteSession"
      />
      
      <div
        v-if="sidebarCollapsed"
        class="flex-1 flex flex-col items-center justify-center bg-gray-50 border-r border-gray-200"
      >
        <button
          @click="sidebarCollapsed = !sidebarCollapsed"
          class="w-8 h-8 bg-blue-500 hover:bg-blue-600 text-white rounded-lg flex items-center justify-center transition-colors"
        >
          <ChevronRight :size="16" />
        </button>
      </div>
      
      <button
        v-if="!sidebarCollapsed"
        @click="sidebarCollapsed = !sidebarCollapsed"
        class="absolute top-1/2 -translate-y-1/2 right-0 w-6 h-12 bg-gray-100 border-r border-t border-b border-gray-200 flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-200 transition-colors"
      >
        <ChevronLeft
          :size="14"
        />
      </button>
    </div>
    
    <div class="flex-1 flex flex-col">
      <header class="h-14 bg-white border-b border-gray-200 flex items-center px-6">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-gradient-to-br from-blue-400 to-purple-500 rounded-lg flex items-center justify-center text-white">
            <MessageCircle :size="18" />
          </div>
          <h1 class="text-lg font-semibold text-gray-800">
            {{ currentSession?.name || '未命名会话' }}
          </h1>
        </div>
      </header>
      
      <ChatArea
        :messages="currentMessages"
        :is-loading="isLoading"
        @send-message="handleSendMessage"
        @clear-history="handleClearHistory"
        @stop-generating="handleStopGenerating"
      />
    </div>
    
    <UsernameSetupModal
      v-if="showUsernameSetup"
      @confirm="handleUsernameConfirm"
    />

    <div
      v-if="showToast"
      class="fixed bottom-4 right-4 px-4 py-2 bg-gray-800 text-white rounded-lg shadow-lg transition-all"
    >
      {{ toastMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { MessageCircle, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import Sidebar from './Sidebar.vue'
import ChatArea from './ChatArea.vue'
import UsernameSetupModal from './UsernameSetupModal.vue'
import { chatStream, getSessions, deleteSession } from '../services/api'
import { sanitizeAssistantContent, shouldSuppressContentDelta, stripLeakedToolContent } from '../utils/messageUtils'
import { getUsername, hasUsername } from '../utils/userStorage'

const sessions = ref([])
const currentSessionId = ref(null)
const messagesBySession = ref({})
const isLoading = ref(false)
const showToast = ref(false)
const toastMessage = ref('')
const sidebarCollapsed = ref(false)
const username = ref(getUsername() || '')
const showUsernameSetup = ref(!hasUsername())
let currentStreamController = null

const currentSession = computed(() => {
  return sessions.value.find(s => s.id === currentSessionId.value)
})

const currentMessages = computed(() => {
  return messagesBySession.value[currentSessionId.value] || []
})

onMounted(async () => {
  await loadSessions()
})

function handleUsernameConfirm(name) {
  username.value = name
  showUsernameSetup.value = false
}

async function loadSessions() {
  try {
    const result = await getSessions()
    sessions.value = result.sessions || []
    
    if (sessions.value.length > 0) {
      currentSessionId.value = sessions.value[0].id
    }
  } catch (e) {
    console.error('加载会话失败:', e)
  }
}

function handleNewSession() {
  const newSession = {
    id: Date.now().toString(),
    name: '未命名会话',
    lastMessage: '',
    createdAt: Date.now()
  }
  sessions.value.unshift(newSession)
  currentSessionId.value = newSession.id
  messagesBySession.value[newSession.id] = []
  
  showToastMessage('已创建新会话')
}

async function handleSelectSession(sessionId) {
  currentSessionId.value = sessionId
  
  if (!messagesBySession.value[sessionId]) {
    messagesBySession.value[sessionId] = []
  }
}

async function handleDeleteSession(sessionId) {
  try {
    await deleteSession(sessionId)
    
    const index = sessions.value.findIndex(s => s.id === sessionId)
    if (index > -1) {
      sessions.value.splice(index, 1)
    }
    
    delete messagesBySession.value[sessionId]
    
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = sessions.value.length > 0 ? sessions.value[0].id : null
    }
    
    showToastMessage('会话已删除')
  } catch (e) {
    console.error('删除会话失败:', e)
    showToastMessage('删除会话失败')
  }
}

async function handleSendMessage(content) {
  if (!currentSessionId.value) {
    handleNewSession()
  }
  
  const sessionId = currentSessionId.value
  
  if (!messagesBySession.value[sessionId]) {
    messagesBySession.value[sessionId] = []
  }
  
  const userMessage = {
    id: Date.now().toString(),
    role: 'user',
    content: content,
    timestamp: Date.now()
  }
  
  messagesBySession.value[sessionId].push(userMessage)
  
  const sessionIndex = sessions.value.findIndex(s => s.id === sessionId)
  if (sessionIndex > -1) {
    sessions.value[sessionIndex].lastMessage = content
    if (!sessions.value[sessionIndex].name || sessions.value[sessionIndex].name === '未命名会话') {
      sessions.value[sessionIndex].name = content.substring(0, 20) + (content.length > 20 ? '...' : '')
    }
  }
  
  isLoading.value = true
  
  const messagesForApi = [{ role: 'user', content }]
  
  try {
    currentStreamController = chatStream(
      sessionId,
      messagesForApi,
      (chunk) => {
        const delta = chunk.choices[0]?.delta || {}
        const deltaContent = delta.content || ''
        const thinking = delta.thinking
        const toolCall = delta.tool_call
        const contentReset = delta.content_reset
        const messages = messagesBySession.value[sessionId]

        if (contentReset) {
          stripLeakedToolContent(messages)
          messagesBySession.value[sessionId] = [...messages]
          return
        }

        if (thinking) {
          stripLeakedToolContent(messages)
          upsertThinkingMessage(messages, thinking)
          messagesBySession.value[sessionId] = [...messages]
        } else if (toolCall) {
          stripLeakedToolContent(messages)
          upsertToolMessage(messages, toolCall)
          messagesBySession.value[sessionId] = [...messages]
        } else if (deltaContent) {
          if (shouldSuppressContentDelta(deltaContent)) return

          const lastMsg = messages[messages.length - 1]
          const merged = lastMsg?.role === 'assistant'
            ? lastMsg.content + deltaContent
            : deltaContent
          const cleanContent = sanitizeAssistantContent(merged)
          if (!cleanContent) return

          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.content = cleanContent
          } else {
            messages.push({
              id: Date.now().toString(),
              role: 'assistant',
              content: cleanContent,
              timestamp: Date.now()
            })
          }
          messagesBySession.value[sessionId] = [...messages]
        }
      },
      (error) => {
        console.error('聊天错误:', error)
        const errorMsg = {
          id: Date.now().toString(),
          role: 'assistant',
          content: '发送失败，请重试',
          timestamp: Date.now()
        }
        messagesBySession.value[sessionId].push(errorMsg)
        messagesBySession.value[sessionId] = [...messagesBySession.value[sessionId]]
        isLoading.value = false
        currentStreamController = null
        showToastMessage('发送失败')
      },
      () => {
        isLoading.value = false
        currentStreamController = null

        const messages = messagesBySession.value[sessionId]
        cleanupMessages(messages)

        const hasAssistant = messages.some(
          m => m.role === 'assistant' && sanitizeAssistantContent(m.content)
        )
        if (!hasAssistant && !messages.some(m => m.role === 'thinking' || m.role === 'tool')) {
          messages.push({
            id: Date.now().toString(),
            role: 'assistant',
            content: '抱歉，未能生成完整回答，请重试。',
            timestamp: Date.now()
          })
        }

        messagesBySession.value[sessionId] = [...messages]
        
        const sessionIdx = sessions.value.findIndex(s => s.id === sessionId)
        if (sessionIdx > -1) {
          const lastAssistantMsg = [...messages].reverse().find(m => m.role === 'assistant')
          if (lastAssistantMsg) {
            sessions.value[sessionIdx].lastMessage = lastAssistantMsg.content.substring(0, 20) + (lastAssistantMsg.content.length > 20 ? '...' : '')
          }
        }
        
        showToastMessage('消息发送成功')
      }
    )
  } catch (e) {
    console.error('聊天异常:', e)
    const errorMsg = {
      id: Date.now().toString(),
      role: 'assistant',
      content: '发送失败，请重试',
      timestamp: Date.now()
    }
    messagesBySession.value[sessionId].push(errorMsg)
    messagesBySession.value[sessionId] = [...messagesBySession.value[sessionId]]
    isLoading.value = false
    currentStreamController = null
    showToastMessage('发送失败')
  }
}

function handleClearHistory() {
  if (currentSessionId.value) {
    messagesBySession.value[currentSessionId.value] = []
    
    const sessionIndex = sessions.value.findIndex(s => s.id === currentSessionId.value)
    if (sessionIndex > -1) {
      sessions.value[sessionIndex].lastMessage = ''
    }
    
    showToastMessage('历史记录已清空')
  }
}

function upsertThinkingMessage(messages, content) {
  messages.push({
    id: `thinking-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    role: 'thinking',
    content,
    timestamp: Date.now()
  })
}

function upsertToolMessage(messages, toolCall) {
  messages.push({
    id: `tool-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    role: 'tool',
    content: '',
    toolCall,
    timestamp: Date.now()
  })
}

function cleanupMessages(messages) {
  stripLeakedToolContent(messages)
}

function showToastMessage(message) {
  toastMessage.value = message
  showToast.value = true
  
  setTimeout(() => {
    showToast.value = false
  }, 2000)
}

function handleStopGenerating() {
  if (currentStreamController) {
    currentStreamController.stop()
    currentStreamController = null
  }
  isLoading.value = false
  showToastMessage('已停止生成')
}
</script>
