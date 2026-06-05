<template>
  <div
    class="h-full bg-gray-50 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden"
  >
    <div class="p-3 border-b border-gray-200 dark:border-gray-700">
      <button
        @click="$emit('new-session')"
        class="w-full flex items-center justify-center gap-2 bg-blue-500 hover:bg-blue-600 text-white py-2.5 px-3 rounded-lg transition-colors font-medium"
      >
        <Plus :size="collapsed ? 20 : 18" />
        <span v-if="!collapsed">新建会话</span>
      </button>
    </div>
    
    <div class="flex-1 overflow-y-auto">
      <div v-if="sessions.length === 0" class="p-4 text-center text-gray-400 dark:text-gray-500">
        <MessageSquare :size="collapsed ? 32 : 48" class="mx-auto mb-2 opacity-50" />
        <p v-if="!collapsed" class="text-sm">暂无会话</p>
      </div>
      
      <div v-else class="p-1 space-y-1">
        <div
          v-for="session in sessions"
          :key="getSessionId(session)"
          @click="$emit('select-session', getSessionId(session))"
          class="group flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-all"
          :class="[
            currentSessionId === getSessionId(session)
              ? 'bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700'
              : 'hover:bg-gray-100 dark:hover:bg-gray-700 border border-transparent'
          ]"
        >
          <div class="flex-shrink-0 w-9 h-9 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white">
            <MessageCircle :size="collapsed ? 16 : 18" />
          </div>
          
          <div v-if="!collapsed" class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
              {{ session.name || '未命名会话' }}
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400 truncate">
              {{ session.lastMessage || '暂无消息' }}
            </p>
          </div>
          
          <button
            v-if="!collapsed"
            @click.stop="$emit('delete-session', getSessionId(session))"
            class="opacity-100 md:opacity-0 md:group-hover:opacity-100 p-1.5 text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-all"
            title="删除会话"
          >
            <Trash2 :size="14" />
          </button>
        </div>
      </div>
    </div>
    
    <div v-if="!collapsed" class="shrink-0 p-3 border-t border-gray-200 dark:border-gray-700 space-y-2">
      <div class="flex items-center gap-2 min-w-0">
        <div class="w-7 h-7 bg-gray-200 dark:bg-gray-600 rounded-full flex items-center justify-center flex-shrink-0">
          <User :size="14" class="text-gray-500 dark:text-gray-300" />
        </div>
        <button
          type="button"
          @click="$emit('edit-username')"
          class="truncate flex-1 text-sm text-gray-500 dark:text-gray-400 text-left hover:text-blue-500 dark:hover:text-blue-400 transition-colors flex items-center gap-1 min-w-0"
          title="修改用户名"
        >
          <span class="truncate">{{ username }}</span>
          <Pencil :size="12" class="flex-shrink-0 opacity-60" />
        </button>
        <button
          type="button"
          @click="$emit('switch-user')"
          class="flex-shrink-0 flex items-center gap-1 px-2 py-1.5 text-xs text-gray-400 dark:text-gray-500 hover:text-blue-500 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
          title="切换用户"
        >
          <Users :size="14" />
          <span>切换</span>
        </button>
      </div>
      <p class="text-xs text-gray-300 dark:text-gray-600 text-center">
        © 2026 NiceBing
      </p>
    </div>
    
    <div v-else class="p-3 border-t border-gray-200 dark:border-gray-700">
      <div class="flex flex-col items-center gap-2">
        <button
          type="button"
          @click="$emit('edit-username')"
          class="w-7 h-7 bg-gray-200 dark:bg-gray-600 rounded-full flex items-center justify-center hover:ring-2 hover:ring-blue-300 dark:hover:ring-blue-600 transition-all"
          title="修改用户名"
        >
          <User :size="14" class="text-gray-500 dark:text-gray-300" />
        </button>
        <button
          type="button"
          @click="$emit('switch-user')"
          class="p-1.5 text-gray-400 dark:text-gray-500 hover:text-blue-500 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
          title="切换用户"
        >
          <Users :size="14" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Plus, MessageSquare, MessageCircle, Trash2, User, Users, Pencil } from 'lucide-vue-next'
import { getSessionId } from '../utils/sessionUtils'

defineProps({
  sessions: {
    type: Array,
    default: () => []
  },
  currentSessionId: {
    type: String,
    default: null
  },
  collapsed: {
    type: Boolean,
    default: false
  },
  username: {
    type: String,
    default: ''
  }
})

defineEmits(['new-session', 'select-session', 'delete-session', 'edit-username', 'switch-user'])
</script>
