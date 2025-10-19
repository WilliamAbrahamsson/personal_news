<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authState, authFetch } from '../lib/auth'

const route = useRoute()
const router = useRouter()
const id = ref(route.params.id)
const loading = ref(false)
const error = ref('')
const source = ref(null)
const videos = ref([])
const vLoading = ref(false)
const vError = ref('')
const newUrl = ref('')

async function load() {
  if (!authState.user) { source.value = null; return }
  loading.value = true
  error.value = ''
  try {
    source.value = await authFetch(`/sources/${id.value}`)
  } catch (e) {
    error.value = e.message || 'Failed to load source'
  } finally {
    loading.value = false
  }
}

async function loadVideos() {
  if (!authState.user || !id.value) { videos.value = []; return }
  vLoading.value = true
  vError.value = ''
  try {
    videos.value = await authFetch(`/sources/${id.value}/videos`)
  } catch (e) {
    vError.value = e.message || 'Failed to load videos'
  } finally {
    vLoading.value = false
  }
}

async function addVideo() {
  if (!newUrl.value.trim()) return
  const tempId = `temp-${Date.now()}`
  const placeholder = {
    id: tempId,
    url: newUrl.value.trim(),
    title: '',
    transcribe_status: 'pending',
    loading: true,
  }
  videos.value.unshift(placeholder)
  const body = { url: placeholder.url }
  authFetch(`/sources/${id.value}/videos`, { method: 'POST', body: JSON.stringify(body) })
    .then((v) => {
      const idx = videos.value.findIndex(x => x.id === tempId)
      if (idx !== -1) videos.value[idx] = v
      else videos.value.unshift(v)
    })
    .catch((e) => {
      const idx = videos.value.findIndex(x => x.id === tempId)
      if (idx !== -1) videos.value.splice(idx, 1)
      alert(e.message || 'Failed to add video')
    })
    .finally(() => {
      newUrl.value = ''
    })
}

async function deleteVideo(v) {
  if (!confirm('Delete this video?')) return
  v._deleting = true
  try {
    await authFetch(`/sources/${id.value}/videos/${v.id}`, { method: 'DELETE' })
    videos.value = videos.value.filter(x => x.id !== v.id)
  } catch (e) {
    alert(e.message || 'Failed to delete video')
  } finally {
    v._deleting = false
  }
}

onMounted(() => { load(); loadVideos() })
watch(() => authState.user, () => { load(); loadVideos() })
watch(() => route.params.id, (v) => { id.value = v; load(); loadVideos() })
</script>

<template>
  <section class="page">
    <button class="back-btn" @click="$router.back()">← Back</button>

    <div v-if="loading" class="center muted">Loading…</div>
    <p v-else-if="error" class="error">{{ error }}</p>

    <div v-else-if="source" class="source-box">
      <div class="source-head">
        <div class="chips">
          <span class="chip">{{ source.type === 'youtube_channel' ? 'YouTube Channel' : source.type }}</span>
          <span v-if="source.label" class="chip">{{ source.label }}</span>
        </div>
        <h1 class="title">{{ source.label || 'YouTube Source' }}</h1>
        <p class="url mono">{{ source.value }}</p>
        <p class="added muted small">
          Added {{ new Date(source.created_at).toLocaleString() }}
        </p>
      </div>
    </div>

    <div class="videos">
      <div class="section-head">
        <h2>Videos</h2>
      </div>

      <div class="add-form">
        <input v-model="newUrl" class="input" placeholder="Paste YouTube link" />
        <button class="btn primary" @click="addVideo" :disabled="!newUrl.trim()">Add</button>
      </div>

      <p v-if="vLoading" class="center muted">Loading videos…</p>
      <p v-if="vError" class="error">{{ vError }}</p>
      <div v-if="!vLoading && videos.length === 0" class="center muted">No videos yet.</div>

      <ul v-else class="video-grid">
        <li v-for="v in videos" :key="v.id" class="video-card" :class="{ loading: v.loading || v.transcribe_status === 'pending' }">
          <div v-if="v.loading || v.transcribe_status === 'pending'" class="loading-card">
            <div class="shimmer"></div>
            <div class="loading-content">
              <svg class="yt" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path fill="currentColor" d="M23.5 6.2s-.2-1.6-.8-2.3c-.8-.8-1.7-.8-2.1-.9C17.9 2.6 12 2.6 12 2.6s-5.9 0-8.6.4c-.4 0-1.4.1-2.1.9C.7 4.6.5 6.2.5 6.2S.2 8.2.2 10.3v1.9c0 2.1.3 4.1.3 4.1s.2 1.6.8 2.3c.8.8 1.9.8 2.4.9 1.7.2 7.3.4 7.3.4s5.9 0 8.6-.4c.4 0 1.4-.1 2.1-.9.6-.7.8-2.3.8-2.3s.3-2 .3-4.1v-1.9c0-2.1-.3-4.1-.3-4.1zM9.7 13.9V7.9l6.2 3-6.2 3z"/>
              </svg>
              <p class="processing-text">Processing video…</p>
            </div>
          </div>

          <div v-else class="clickable-card" @click="router.push(`/sources/${id}/videos/${v.id}`)">
            <div class="content">
              <div class="v-head">
                <svg class="yt" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M23.5 6.2s-.2-1.6-.8-2.3c-.8-.8-1.7-.8-2.1-.9C17.9 2.6 12 2.6 12 2.6s-5.9 0-8.6.4c-.4 0-1.4.1-2.1.9C.7 4.6.5 6.2.5 6.2S.2 8.2.2 10.3v1.9c0 2.1.3 4.1.3 4.1s.2 1.6.8 2.3c.8.8 1.9.8 2.4.9 1.7.2 7.3.4 7.3.4s5.9 0 8.6-.4c.4 0 1.4-.1 2.1-.9.6-.7.8-2.3.8-2.3s.3-2 .3-4.1v-1.9c0-2.1-.3-4.1-.3-4.1zM9.7 13.9V7.9l6.2 3-6.2 3z"/>
                </svg>
                <h3 class="v-title">{{ v.title || v.url }}</h3>
              </div>
              <p class="muted small mono truncate">{{ v.url }}</p>
              <p class="added small muted">Added {{ new Date(v.created_at).toLocaleString() }}</p>
            </div>

            <div class="actions" @click.stop>
              <a class="btn small outline" :href="v.url" target="_blank">Watch</a>
              <button class="btn small danger" @click="deleteVideo(v)" :disabled="v._deleting">{{ v._deleting ? 'Deleting…' : 'Delete' }}</button>
            </div>
          </div>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2.618rem 1.618rem;
  color: var(--text);
}
.center { text-align: center; }
.muted { color: var(--muted); }
.small { font-size: 13px; }
.mono { font-family: ui-monospace, monospace; word-break: break-all; }
.error { color: var(--red); }

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #ddd;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 1.618rem;
  transition: all 0.2s ease;
}
.back-btn:hover {
  background: #333;
  border-color: #555;
  color: #fff;
}
.back-btn:active {
  background: #3a3a3a;
  transform: translateY(1px);
}

.source-box {
  background: #222;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1.618rem;
  margin-bottom: 2.618rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.2);
}
.source-head .title {
  font-size: 1.75rem;
  margin: 0.5rem 0;
  line-height: 1.2;
}
.url { font-size: 0.95rem; margin: 0.25rem 0 0.75rem; }
.chips { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.chip {
  background: #2b2b2b;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  color: #ccc;
}

.add-form {
  display: flex;
  gap: 0.618rem;
  margin-bottom: 1.618rem;
}
.input {
  flex: 1;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #333;
  background: #1a1a1a;
  color: #ddd;
}
.input:focus { outline: 1px solid #666; }

.btn {
  background: #444;
  color: #eee;
  border: 1px solid #555;
  border-radius: 8px;
  padding: 8px 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn.small { padding: 6px 10px; font-size: 13px; }
.btn.danger { background: var(--red); border-color: transparent; color: #fff; }
.btn:hover { background: #555; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn.outline { background: transparent; border: 1px solid #555; }
.btn.outline:hover { background: #333; }

.video-grid {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 1.618rem;
  margin: 0;
  padding: 0;
}
.video-card {
  position: relative;
  background: #1d1d1d;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1.618rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.2);
  transition: all 0.25s ease;
}
.video-card:hover {
  transform: translateY(-2px);
  border-color: #555;
  box-shadow: 0 4px 10px rgba(0,0,0,0.25);
}

.loading-card {
  position: relative;
  height: 150px;
  border-radius: 10px;
  background: #1d1d1d;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #aaa;
}
.shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%);
  animation: shimmerMove 1.8s linear infinite;
}
@keyframes shimmerMove {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.loading-content {
  position: relative;
  z-index: 1;
  text-align: center;
}
.processing-text {
  font-size: 0.9rem;
  color: #bbb;
  margin-top: 0.5rem;
}

.clickable-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  height: 100%;
}
.content { flex: 1; display: flex; flex-direction: column; gap: 0.618rem; }
.v-head { display: flex; align-items: center; gap: 8px; }
.v-title { margin: 0; font-size: 1rem; color: #ddd; font-weight: 600; }
.yt { width: 20px; height: 20px; color: #c4302b; flex-shrink: 0; }
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.actions {
  display: flex;
  gap: 0.618rem;
  justify-content: flex-start;
  margin-top: auto;
  padding-top: 0.618rem;
}
</style>
