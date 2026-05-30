<template>
  <div
    v-html="renderedContent"
    class="markdown-content"
  ></div>
</template>

<script setup>
import { computed } from 'vue'
import markdownit from 'markdown-it'
import hljs from 'highlight.js'

const props = defineProps({
  content: {
    type: String,
    default: ''
  }
})

const md = markdownit({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value
      } catch (_) {}
    }
    return ''
  },
})

const renderedContent = computed(() => {
  if (!props.content) return ''
  return md.render(props.content)
})
</script>
