<script setup>
import { ref, onMounted } from 'vue'
import Layout from './components/Layout.vue'
import ShareView from './components/ShareView.vue'

const shareSessionId = ref(null)

onMounted(() => {
  const match = window.location.pathname.match(/^\/share\/([^/]+)\/?$/)
  shareSessionId.value = match ? decodeURIComponent(match[1]) : null
})
</script>

<template>
  <ShareView v-if="shareSessionId" :session-id="shareSessionId" />
  <Layout v-else />
</template>
