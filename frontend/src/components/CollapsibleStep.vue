<template>
  <div class="group rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 overflow-hidden">
    <button
      type="button"
      class="w-full flex items-center gap-2.5 px-3 py-2.5 text-left hover:bg-gray-100/90 dark:hover:bg-gray-700/90 transition-colors"
      @click="expanded = !expanded"
    >
      <component :is="icon" :size="16" class="flex-shrink-0 text-gray-500 dark:text-gray-400" />
      <span class="text-sm text-gray-600 dark:text-gray-300 truncate">{{ title }}</span>
      <ChevronDown
        :size="15"
        class="ml-auto flex-shrink-0 text-gray-400 dark:text-gray-500 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-all duration-200"
        :class="{ 'rotate-180 opacity-100': expanded }"
      />
    </button>

    <div
      v-show="expanded"
      class="px-3 pb-3 pt-0 text-sm text-gray-500 dark:text-gray-400 leading-relaxed whitespace-pre-wrap break-words border-t border-gray-100 dark:border-gray-700"
    >
      <slot>{{ detail }}</slot>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Lightbulb, Wrench, ChevronDown } from 'lucide-vue-next'
import { formatToolStepSummary } from '../utils/messageUtils'

const props = defineProps({
  step: {
    type: Object,
    required: true,
  },
})

const expanded = ref(false)

const icon = computed(() => (props.step.type === 'thinking' ? Lightbulb : Wrench))

const title = computed(() => {
  if (props.step.type === 'thinking') return '思考过程'
  return props.step.toolCall?.name || 'tool'
})

const detail = computed(() => {
  if (props.step.type === 'thinking') {
    return props.step.content || ''
  }
  const tc = props.step.toolCall
  if (!tc) return ''
  const lines = []
  if (Object.keys(tc.arguments || {}).length) {
    lines.push(JSON.stringify(tc.arguments, null, 2))
  }
  if (tc.result) {
    lines.push('\n' + tc.result)
  }
  return lines.join('').trim() || formatToolStepSummary(tc)
})
</script>
