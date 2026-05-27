<template>
  <div
    class="flex gap-3 mb-4"
    :class="[
      message.role === 'user' ? 'flex-row-reverse' : message.role === 'thinking' || message.role === 'tool' ? 'flex-row justify-center' : 'flex-row'
    ]"
  >
    <template v-if="message.role === 'thinking'">
      <div class="w-full max-w-3xl">
        <div
          class="bg-amber-50 border border-amber-200 rounded-xl overflow-hidden"
        >
          <div
            class="flex items-center gap-2 px-4 py-2 bg-amber-100 cursor-pointer hover:bg-amber-200 transition-colors"
            @click="toggleExpand('thinking')"
          >
            <Lightbulb :size="16" class="text-amber-600" />
            <span class="text-sm font-medium text-amber-700">思考中</span>
            <ChevronDown
              :size="14"
              class="ml-auto text-amber-600 transition-transform"
              :class="{ 'rotate-180': expanded.thinking }"
            />
          </div>
          <div
            v-show="expanded.thinking"
            class="px-4 py-3"
          >
            <p class="text-sm text-amber-800">{{ message.content }}</p>
          </div>
        </div>
      </div>
    </template>

    <template v-else-if="message.role === 'tool'">
      <div class="w-full max-w-3xl">
        <div
          class="bg-blue-50 border border-blue-200 rounded-xl overflow-hidden"
        >
          <div
            class="flex items-center gap-2 px-4 py-2 bg-blue-100 cursor-pointer hover:bg-blue-200 transition-colors"
            @click="toggleExpand('tool')"
          >
            <Wrench :size="16" class="text-blue-600" />
            <span class="text-sm font-medium text-blue-700">
              工具调用: {{ message.toolCall?.name }}
            </span>
            <ChevronDown
              :size="14"
              class="ml-auto text-blue-600 transition-transform"
              :class="{ 'rotate-180': expanded.tool }"
            />
          </div>
          <div
            v-show="expanded.tool"
            class="px-4 py-3 space-y-3"
          >
            <div class="bg-gray-50 rounded-lg p-3">
              <p class="text-xs text-gray-500 mb-1">参数</p>
              <pre class="text-sm text-gray-700 font-mono">{{ JSON.stringify(message.toolCall?.arguments || {}, null, 2) }}</pre>
            </div>
            <div class="bg-gray-50 rounded-lg p-3">
              <p class="text-xs text-gray-500 mb-1">结果</p>
              <pre class="text-sm text-gray-700 font-mono max-h-60 overflow-auto">{{ message.toolCall?.result || '' }}</pre>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <div
        class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center"
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
        class="max-w-[70%] px-4 py-3 rounded-2xl"
        :class="[
          message.role === 'user'
            ? 'bg-blue-500 text-white rounded-tr-sm'
            : 'bg-gray-100 text-gray-800 rounded-tl-sm'
        ]"
      >
        <div v-if="message.role !== 'user'" class="flex items-center gap-2 mb-2">
          <span class="text-sm font-medium text-gray-600">Agent</span>
          <span class="text-xs text-gray-400">{{ formatTime(message.timestamp) }}</span>
        </div>
        
        <div
          v-if="message.role === 'user'"
          class="text-white"
        >
          {{ message.content }}
        </div>
        
        <MarkdownRenderer
          v-else
          :content="message.content"
          class="markdown-content"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { User, Bot, Lightbulb, ChevronDown, Wrench } from 'lucide-vue-next'
import MarkdownRenderer from './MarkdownRenderer.vue'

defineProps({
  message: {
    type: Object,
    required: true
  }
})

const expanded = reactive({
  thinking: true,
  tool: true
})

function toggleExpand(type) {
  expanded[type] = !expanded[type]
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>
