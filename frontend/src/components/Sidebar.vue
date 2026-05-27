<template>
  <div class="w-72 h-full bg-gray-50 border-r border-gray-200 flex flex-col">
    <div class="p-4 border-b border-gray-200">
      <button
        @click="$emit('new-session')"
        class="w-full flex items-center justify-center gap-2 bg-blue-500 hover:bg-blue-600 text-white py-2.5 px-4 rounded-lg transition-colors font-medium"
      >
        <Plus :size="18" />
        <span>新建会话</span>
      </button>
    </div>
    
    <div class="flex-1 overflow-y-auto">
      <div v-if="sessions.length === 0" class="p-4 text-center text-gray-400">
        <MessageSquare :size="48" class="mx-auto mb-2 opacity-50" />
        <p>暂无会话</p>
      </div>
      
      <div v-else class="p-2 space-y-1">
        <div
          v-for="session in sessions"
          :key="session.id"
          @click="$emit('select-session', session.id)"
          class="group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all"
          :class="[
            currentSessionId === session.id
              ? 'bg-blue-50 border border-blue-200'
              : 'hover:bg-gray-100 border border-transparent'
          ]"
        >
          <div class="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white">
            <MessageCircle :size="18" />
          </div>
          
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-800 truncate">
              {{ session.name || '未命名会话' }}
            </p>
            <p class="text-xs text-gray-500 truncate">
              {{ session.lastMessage || '暂无消息' }}
            </p>
          </div>
          
          <button
            @click.stop="$emit('delete-session', session.id)"
            class="opacity-0 group-hover:opacity-100 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-all"
            title="删除会话"
          >
            <Trash2 :size="14" />
          </button>
        </div>
      </div>
    </div>
    
    <div class="p-4 border-t border-gray-200">
      <div class="flex items-center gap-3 text-sm text-gray-500">
        <div class="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
          <User :size="16" />
        </div>
        <span>AgentScope Chat</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Plus, MessageSquare, MessageCircle, Trash2, User } from 'lucide-vue-next'

defineProps({
  sessions: {
    type: Array,
    default: () => []
  },
  currentSessionId: {
    type: String,
    default: null
  }
})

defineEmits(['new-session', 'select-session', 'delete-session'])
</script>
