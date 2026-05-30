<template>
  <div class="flex gap-3 mb-4 flex-row">
    <div class="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white">
      <Bot :size="18" />
    </div>
    <div class="bg-gray-100 px-4 py-3 rounded-2xl rounded-tl-sm">
      <div class="flex gap-1">
        <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms" />
        <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms" />
        <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { Bot } from 'lucide-vue-next'
</script>
