<template>
  <div
    class="h-full bg-gray-50 border-r border-gray-200 flex flex-col overflow-hidden"
  >
    <div class="p-3 border-b border-gray-200">
      <button
        @click="$emit('new-session')"
        class="w-full flex items-center justify-center gap-2 bg-blue-500 hover:bg-blue-600 text-white py-2.5 px-3 rounded-lg transition-colors font-medium"
      >
        <Plus :size="collapsed ? 20 : 18" />
        <span v-if="!collapsed">新建会话</span>
      </button>
    </div>
    
    <div class="flex-1 overflow-y-auto">
      <div v-if="sessions.length === 0" class="p-4 text-center text-gray-400">
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
              ? 'bg-blue-50 border border-blue-200'
              : 'hover:bg-gray-100 border border-transparent'
          ]"
        >
          <div class="flex-shrink-0 w-9 h-9 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white">
            <MessageCircle :size="collapsed ? 16 : 18" />
          </div>
          
          <div v-if="!collapsed" class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-800 truncate">
              {{ session.name || '未命名会话' }}
            </p>
            <p class="text-xs text-gray-500 truncate">
              {{ session.lastMessage || '暂无消息' }}
            </p>
          </div>
          
          <button
            v-if="!collapsed"
            @click.stop="$emit('delete-session', getSessionId(session))"
            class="opacity-100 md:opacity-0 md:group-hover:opacity-100 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-all"
            title="删除会话"
          >
            <Trash2 :size="14" />
          </button>
        </div>
      </div>
    </div>
    
    <div v-if="!collapsed" class="p-3 border-t border-gray-200">
      <div class="flex items-center gap-2 text-sm text-gray-500 min-w-0">
        <div class="w-7 h-7 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
          <User :size="14" />
        </div>
        <span class="truncate">{{ username }}</span>
      </div>
    </div>
    
    <div v-else class="p-3 border-t border-gray-200">
      <div class="flex justify-center">
        <div class="w-7 h-7 bg-gray-200 rounded-full flex items-center justify-center">
          <User :size="14" class="text-gray-500" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Plus, MessageSquare, MessageCircle, Trash2, User } from 'lucide-vue-next'
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

defineEmits(['new-session', 'select-session', 'delete-session'])
</script>
