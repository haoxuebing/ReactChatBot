<template>
  <button
    type="button"
    @click="toggleTheme"
    class="p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 rounded-lg transition-colors"
    :title="isDark ? '切换为浅色模式' : '切换为深色模式'"
    :aria-label="isDark ? '切换为浅色模式' : '切换为深色模式'"
  >
    <Sun v-if="isDark" :size="20" />
    <Moon v-else :size="20" />
  </button>
</template>

<script setup>
import { Sun, Moon } from 'lucide-vue-next'
import { isDark, toggleTheme } from '../composables/useTheme'
</script>
