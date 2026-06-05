<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
    <div class="w-full max-w-sm bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6">
      <div class="w-12 h-12 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white mx-auto mb-4">
        <User :size="24" />
      </div>
      <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100 text-center mb-1">
        {{ mode === 'edit' ? '修改用户名' : '切换用户' }}
      </h2>
      <p class="text-sm text-gray-400 dark:text-gray-500 text-center mb-5">{{ subtitleText }}</p>

      <div v-if="mode === 'switch' && recentUsers.length > 0" class="mb-4">
        <p class="text-xs text-gray-400 dark:text-gray-500 mb-2">最近使用</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="name in recentUsers"
            :key="name"
            type="button"
            @click="selectRecentUser(name)"
            class="px-3 py-1.5 text-sm rounded-lg border transition-colors truncate max-w-full"
            :class="inputValue === name
              ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300'
              : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-blue-300 dark:hover:border-blue-600'"
          >
            {{ name }}
          </button>
        </div>
      </div>

      <input
        v-model="inputValue"
        type="text"
        maxlength="12"
        :placeholder="mode === 'edit' ? '请输入新用户名' : '输入用户名或选择上方'"
        class="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-xl outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 dark:focus:ring-blue-900 text-gray-800 dark:text-gray-100"
        @keydown.enter="handleConfirm"
      />
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-2 text-right">{{ inputValue.length }}/12</p>
      <p v-if="errorMessage" class="text-xs text-red-500 mt-2 text-center">{{ errorMessage }}</p>

      <div class="mt-4 space-y-2">
        <button
          v-if="mode === 'switch'"
          type="button"
          @click="handleCreateAnonymous"
          class="w-full py-2.5 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-xl font-medium transition-colors"
        >
          新建匿名用户
        </button>
        <button
          type="button"
          @click="handleConfirm"
          :disabled="!canConfirm"
          class="w-full py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-colors"
        >
          {{ mode === 'edit' ? '保存' : '切换' }}
        </button>
        <button
          type="button"
          @click="$emit('cancel')"
          class="w-full py-2 text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        >
          取消
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { User } from 'lucide-vue-next'
import { generateAnonymousUsername, saveUsername } from '../utils/userStorage'

const props = defineProps({
  mode: {
    type: String,
    default: 'switch',
    validator: (value) => ['edit', 'switch'].includes(value),
  },
  currentUsername: {
    type: String,
    default: '',
  },
  recentUsers: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['confirm', 'cancel'])

const inputValue = ref('')
const errorMessage = ref('')

const subtitleText = computed(() => {
  if (props.mode === 'edit') {
    return '修改后将切换到新身份，原会话仍保留在原用户名下'
  }
  return '选择已有用户、输入新名称，或创建匿名用户'
})

const canConfirm = computed(() => inputValue.value.trim().length > 0)

watch(
  () => [props.mode, props.currentUsername],
  () => {
    inputValue.value = props.mode === 'edit' ? props.currentUsername : ''
    errorMessage.value = ''
  },
  { immediate: true },
)

function selectRecentUser(name) {
  inputValue.value = name
  errorMessage.value = ''
}

function handleCreateAnonymous() {
  const username = generateAnonymousUsername()
  inputValue.value = username
  errorMessage.value = ''
  emit('confirm', username)
}

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
