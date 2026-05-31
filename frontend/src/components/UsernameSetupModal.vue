<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
    <div class="w-full max-w-sm bg-white rounded-2xl shadow-xl p-6">
      <div class="w-12 h-12 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white mx-auto mb-4">
        <User :size="24" />
      </div>
      <h2 class="text-lg font-semibold text-gray-800 text-center mb-1">设置用户名</h2>
      <p class="text-sm text-gray-400 text-center mb-5">{{ subtitle }}</p>

      <input
        v-model="inputValue"
        type="text"
        maxlength="12"
        placeholder="请输入用户名"
        class="w-full px-4 py-2.5 border border-gray-200 rounded-xl outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 text-gray-800"
        @keydown.enter="handleConfirm"
      />
      <p class="text-xs text-gray-400 mt-2 text-right">{{ inputValue.length }}/12</p>
      <p v-if="errorMessage" class="text-xs text-red-500 mt-2 text-center">{{ errorMessage }}</p>

      <button
        @click="handleConfirm"
        :disabled="!canConfirm"
        class="w-full mt-4 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-colors"
      >
        开始使用
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { User } from 'lucide-vue-next'
import { saveUsername } from '../utils/userStorage'

defineProps({
  subtitle: {
    type: String,
    default: '首次使用请先设置一个显示名称',
  },
})

const emit = defineEmits(['confirm'])

const inputValue = ref('')
const errorMessage = ref('')

const canConfirm = computed(() => inputValue.value.trim().length > 0)

function handleConfirm() {
  errorMessage.value = ''
  const username = saveUsername(inputValue.value)
  if (!username) {
    errorMessage.value = '请输入用户名'
    return
  }
  emit('confirm', username)
}
</script>
