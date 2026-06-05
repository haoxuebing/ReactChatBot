<template>
  <div class="h-dvh flex bg-gray-100 dark:bg-gray-900 overflow-hidden">
    <!-- 移动端：遮罩 + 抽屉（不参与 flex 布局） -->
    <div
      v-if="mobileSidebarOpen"
      class="fixed inset-0 z-40 bg-black/40 md:hidden"
      @click="mobileSidebarOpen = false"
    />
    <aside
      class="md:hidden fixed inset-y-0 left-0 z-50 w-[min(85vw,18rem)] bg-gray-50 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 shadow-xl transition-transform duration-300"
      :class="mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full pointer-events-none'"
    >
      <Sidebar
        :sessions="sessions"
        :current-session-id="currentSessionId"
        :collapsed="false"
        :username="username"
        @new-session="handleNewSession"
        @select-session="handleSelectSession"
        @delete-session="handleDeleteSession"
        @edit-username="handleEditUsername"
        @switch-user="handleSwitchUser"
      />
    </aside>

    <!-- 桌面端：侧边栏 -->
    <div
      class="hidden md:flex flex-col h-full transition-all duration-300 relative shrink-0 bg-gray-50 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700"
      :class="sidebarCollapsed ? 'w-12' : 'w-72'"
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
        @edit-username="handleEditUsername"
        @switch-user="handleSwitchUser"
      />

      <div
        v-if="sidebarCollapsed"
        class="flex-1 flex flex-col items-center justify-center"
      >
        <button
          @click="sidebarCollapsed = false"
          class="w-8 h-8 bg-blue-500 hover:bg-blue-600 text-white rounded-lg flex items-center justify-center transition-colors"
        >
          <ChevronRight :size="16" />
        </button>
      </div>

      <button
        v-if="!sidebarCollapsed"
        @click="sidebarCollapsed = true"
        class="absolute top-1/2 -translate-y-1/2 right-0 w-6 h-12 bg-gray-100 dark:bg-gray-700 border-r border-t border-b border-gray-200 dark:border-gray-600 flex items-center justify-center text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
      >
        <ChevronLeft :size="14" />
      </button>
    </div>

    <!-- 主内容区（小屏占满全宽） -->
    <div class="flex-1 flex flex-col min-w-0 min-h-0 overflow-hidden w-full">
      <header class="h-14 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center px-3 md:px-6 gap-2 md:gap-3 shrink-0">
        <button
          @click="mobileSidebarOpen = true"
          class="md:hidden p-2 -ml-1 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          aria-label="打开菜单"
        >
          <Menu :size="20" />
        </button>
        <div class="flex items-center gap-2 md:gap-3 min-w-0 flex-1">
          <div class="w-8 h-8 bg-gradient-to-br from-blue-400 to-purple-500 rounded-lg flex items-center justify-center text-white shrink-0">
            <MessageCircle :size="18" />
          </div>
          <h1 class="text-base md:text-lg font-semibold text-gray-800 dark:text-gray-100 truncate">
            {{ currentSession?.name || '未命名会话' }}
          </h1>
        </div>
        <ThemeToggle />
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
      v-if="showUsernameModal"
      :mode="usernameModalMode"
      :current-username="username"
      :recent-users="recentUsers"
      @confirm="handleUsernameConfirm"
      @cancel="showUsernameModal = false"
    />

    <div
      v-if="showToast"
      class="fixed bottom-4 right-4 px-4 py-2 bg-gray-800 dark:bg-gray-700 text-white rounded-lg shadow-lg transition-all mb-safe"
    >
      {{ toastMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { MessageCircle, ChevronLeft, ChevronRight, Menu } from 'lucide-vue-next'
import Sidebar from './Sidebar.vue'
import ChatArea from './ChatArea.vue'
import UsernameSetupModal from './UsernameSetupModal.vue'
import ThemeToggle from './ThemeToggle.vue'
import { chatStream, getSessions, getSession, deleteSession, registerUser, createSession } from '../services/api'
import { sanitizeAssistantContent, shouldSuppressContentDelta, stripLeakedToolContent } from '../utils/messageUtils'
import { normalizeSession, apiMessagesToLocal, deriveSessionMetaFromMessages } from '../utils/sessionUtils'
import { ensureUsername, saveUsername, addRecentUser, getRecentUsers } from '../utils/userStorage'
import { messageTimestamp } from '../utils/messageTimestamp'

const sessions = ref([])
const currentSessionId = ref(null)
const messagesBySession = ref({})
const isLoading = ref(false)
const showToast = ref(false)
const toastMessage = ref('')
const sidebarCollapsed = ref(false)
const mobileSidebarOpen = ref(false)
const username = ref('')
const showUsernameModal = ref(false)
const usernameModalMode = ref('switch')
const recentUsers = ref([])
let currentStreamController = null

const currentSession = computed(() => {
  return sessions.value.find(s => s.id === currentSessionId.value)
})

const currentMessages = computed(() => {
  return messagesBySession.value[currentSessionId.value] || []
})

onMounted(async () => {
  await initUser()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

function handleResize() {
  if (window.innerWidth >= 768) {
    mobileSidebarOpen.value = false
  }
}

function closeMobileSidebar() {
  mobileSidebarOpen.value = false
}

function stopCurrentStream() {
  if (currentStreamController) {
    currentStreamController.stop()
    currentStreamController = null
  }
  isLoading.value = false
}

function refreshRecentUsers() {
  recentUsers.value = getRecentUsers()
}

async function initUser() {
  const name = ensureUsername()
  username.value = name
  refreshRecentUsers()
  try {
    await registerUser(name)
    await loadSessions()
  } catch (e) {
    console.error('初始化用户失败:', e)
    showToastMessage('加载用户会话失败')
  }
}

async function activateUser(name) {
  const trimmed = saveUsername(name)
  if (!trimmed) return

  if (trimmed === username.value) {
    showUsernameModal.value = false
    return
  }

  stopCurrentStream()
  addRecentUser(trimmed)
  username.value = trimmed
  refreshRecentUsers()
  showUsernameModal.value = false

  sessions.value = []
  currentSessionId.value = null
  messagesBySession.value = {}

  try {
    await registerUser(trimmed)
    await loadSessions()
    closeMobileSidebar()
    showToastMessage(`已切换到 ${trimmed}`)
  } catch (e) {
    console.error('切换用户失败:', e)
    showToastMessage('切换用户失败')
  }
}

async function handleUsernameConfirm(name) {
  await activateUser(name)
}

function handleEditUsername() {
  usernameModalMode.value = 'edit'
  refreshRecentUsers()
  showUsernameModal.value = true
}

function handleSwitchUser() {
  usernameModalMode.value = 'switch'
  refreshRecentUsers()
  showUsernameModal.value = true
}

async function loadSessions() {
  if (!username.value) return

  try {
    const result = await getSessions(username.value)
    sessions.value = (result.sessions || []).map(normalizeSession)

    if (sessions.value.length > 0) {
      const firstId = sessions.value[0].id
      currentSessionId.value = firstId
      await loadSessionMessages(firstId)
    } else {
      currentSessionId.value = null
    }
  } catch (e) {
    console.error('加载会话失败:', e)
  }
}

async function loadSessionMessages(sessionId) {
  if (!sessionId) return

  try {
    const result = await getSession(sessionId)
    const session = result.session
    if (!session || session.error) {
      if (!messagesBySession.value[sessionId]) {
        messagesBySession.value[sessionId] = []
      }
      return
    }

    const localMessages = apiMessagesToLocal(sessionId, session.messages)
    messagesBySession.value[sessionId] = localMessages

    const sessionIndex = sessions.value.findIndex(s => s.id === sessionId)
    if (sessionIndex > -1) {
      const meta = deriveSessionMetaFromMessages(localMessages)
      sessions.value[sessionIndex] = {
        ...sessions.value[sessionIndex],
        name: meta.name,
        lastMessage: meta.lastMessage,
        messageCount: session.message_count ?? localMessages.length,
      }
    }
  } catch (e) {
    console.error('加载会话消息失败:', e)
    if (!messagesBySession.value[sessionId]) {
      messagesBySession.value[sessionId] = []
    }
  }
}

async function handleNewSession() {
  const sessionId = Date.now().toString()

  try {
    await createSession(username.value, sessionId)
  } catch (e) {
    console.error('创建会话失败:', e)
    showToastMessage('创建会话失败')
    return
  }

  const newSession = {
    id: sessionId,
    name: '未命名会话',
    lastMessage: '',
    createdAt: Date.now()
  }
  sessions.value.unshift(newSession)
  currentSessionId.value = newSession.id
  messagesBySession.value[newSession.id] = []

  closeMobileSidebar()
  showToastMessage('已创建新会话')
}

async function handleSelectSession(sessionId) {
  if (currentSessionId.value === sessionId) {
    closeMobileSidebar()
    return
  }

  if (isLoading.value && currentStreamController) {
    currentStreamController.stop()
    currentStreamController = null
    isLoading.value = false
  }

  currentSessionId.value = sessionId
  await loadSessionMessages(sessionId)
  closeMobileSidebar()
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
    await handleNewSession()
  }

  const sessionId = currentSessionId.value
  
  if (!messagesBySession.value[sessionId]) {
    messagesBySession.value[sessionId] = []
  }
  
  const userMessage = {
    id: Date.now().toString(),
    role: 'user',
    content: content,
    timestamp: messageTimestamp()
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
      username.value,
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

          // 流式阶段只做拼接，不做 trim/清洗，避免吃掉行尾换行导致代码挤在一行
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.content = merged
          } else {
            messages.push({
              id: Date.now().toString(),
              role: 'assistant',
              content: merged,
              timestamp: messageTimestamp()
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
          timestamp: messageTimestamp()
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
        if (!hasAssistant) {
          messages.push({
            id: Date.now().toString(),
            role: 'assistant',
            content: '抱歉，未能生成完整回答，请重试。',
            timestamp: messageTimestamp()
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
      timestamp: messageTimestamp()
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
    timestamp: messageTimestamp()
  })
}

function upsertToolMessage(messages, toolCall) {
  messages.push({
    id: `tool-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    role: 'tool',
    content: '',
    toolCall,
    timestamp: messageTimestamp()
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
