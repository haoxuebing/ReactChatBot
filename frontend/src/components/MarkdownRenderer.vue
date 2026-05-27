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
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value
      } catch (__) {}
    }
    return ''
  },
  html: true,
  linkify: true,
  typographer: true
})

const renderedContent = computed(() => {
  if (!props.content) return ''
  return md.render(props.content)
})
</script>
