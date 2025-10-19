<script setup>
import { ref, onMounted, watch, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { authState, authFetch } from '../lib/auth'

const route = useRoute()
const sourceId = ref(route.params.sourceId)
const videoId = ref(route.params.videoId)

const loading = ref(false)
const error = ref('')
const video = ref(null)
const editing = ref(false)
const editTranscribe = ref('')
const showTranscribe = ref(false)
const renderedSummary = ref('')

function mdToHtml(md) {
  let esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  md = esc(md || '')
  md = md.replace(/^######\s+(.*)$/gm, '<h6>$1</h6>')
         .replace(/^#####\s+(.*)$/gm, '<h5>$1</h5>')
         .replace(/^####\s+(.*)$/gm, '<h4>$1</h4>')
         .replace(/^###\s+(.*)$/gm, '<h3>$1</h3>')
         .replace(/^##\s+(.*)$/gm, '<h2>$1</h2>')
         .replace(/^#\s+(.*)$/gm, '<h1>$1</h1>')
  md = md.replace(/\*\*(.+?)\*\*/g, '<strong>$1<\/strong>')
         .replace(/\*(.+?)\*/g, '<em>$1<\/em>')
  md = md.replace(/(^|\n)(-\s.+(?:\n-\s.+)*)/g, (m, p1, block) => {
    const items = block.split(/\n/).map(l => l.replace(/^-\s+/, '')).map(li => `<li>${li}<\/li>`).join('')
    return `${p1}<ul>${items}<\/ul>`
  })
  md = md.replace(/\n{2,}/g, '</p><p>')
  md = `<p>${md}</p>`
  return md
}

function updateRenderedSummary() {
  renderedSummary.value = mdToHtml(video.value?.summary || '')
}

const aiLoading = ref(false)
const aiError = ref('')
const polling = ref(null)

const isPipelineRunning = computed(() =>
  video.value && (video.value.audio_status === 'pending' || video.value.transcribe_status === 'pending')
)
const isPipelineDone = computed(() =>
  video.value && video.value.transcribe_status === 'ready'
)

async function load() {
  if (!authState.user) { video.value = null; return }
  loading.value = true
  error.value = ''
  try {
    video.value = await authFetch(`/sources/${sourceId.value}/videos/${videoId.value}`)
    editTranscribe.value = video.value?.transcribe || ''
    updateRenderedSummary()
  } catch (e) {
    error.value = e.message || 'Failed to load video'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  polling.value = setInterval(async () => {
    if (!authState.user) return
    try {
      const v = await authFetch(`/sources/${sourceId.value}/videos/${videoId.value}`)
      if (video.value) {
        const changed =
          v.audio_status !== video.value.audio_status ||
          v.transcribe_status !== video.value.transcribe_status ||
          v.summary !== video.value.summary ||
          v.transcribe !== video.value.transcribe
        if (changed) {
          video.value = v
          if (!editing.value) editTranscribe.value = v.transcribe || ''
          updateRenderedSummary()
        }
      } else {
        video.value = v
        updateRenderedSummary()
      }
      if (v.audio_status === 'ready' && (v.transcribe_status === 'ready' || v.transcribe_status === 'failed' || (v.transcribe || '').length > 0)) {
        stopPolling()
      }
    } catch {}
    if (video.value && video.value.transcribe_status === 'ready') stopPolling()
  }, 1000)
}

function stopPolling() {
  if (polling.value) {
    clearInterval(polling.value)
    polling.value = null
  }
}

async function saveTranscribe() {
  try {
    const updated = await authFetch(`/sources/${sourceId.value}/videos/${videoId.value}`, {
      method: 'PATCH',
      body: JSON.stringify({ transcribe: editTranscribe.value })
    })
    video.value = updated
    editing.value = false
    updateRenderedSummary()
  } catch (e) {
    alert(e.message || 'Failed to save')
  }
}

async function clearTranscribe() {
  editTranscribe.value = ''
  await saveTranscribe()
}

async function summarizeWithAI() {
  aiLoading.value = true
  aiError.value = ''
  try {
    const res = await authFetch(`/ai/videos/${videoId.value}/summarize`, {
      method: 'POST',
      body: JSON.stringify({})
    })
    if (res && res.video) {
      video.value = res.video
      updateRenderedSummary()
    }
  } catch (e) {
    aiError.value = e.message || 'Failed to summarize'
  } finally {
    aiLoading.value = false
  }
}

onMounted(() => { load(); startPolling() })
watch(() => authState.user, load)
watch(() => route.params.videoId, (v) => { videoId.value = v; load() })
onUnmounted(stopPolling)
</script>

<template>
  <section class="page">
    <button class="back-btn" @click="$router.back()">← Back</button>
    <h1>Video Details</h1>

    <p v-if="!authState.user" class="muted">Please sign in to view this video.</p>
    <p v-else-if="loading" class="muted">Loading…</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <div v-else-if="video" class="card">
      <div class="row">
        <div class="label">Title</div>
        <div>{{ video.title || '—' }}</div>
      </div>
      <div class="row">
        <div class="label">URL</div>
        <div><a :href="video.url" target="_blank" class="link-url">Open video ↗</a></div>
      </div>
      <div class="row">
        <div class="label">Added</div>
        <div>{{ new Date(video.created_at).toLocaleString() }}</div>
      </div>
    </div>

    <div v-if="video && authState.user && isPipelineRunning" class="loading-card">
      <div class="shimmer-line title"></div>
      <div class="shimmer-line"></div>
      <div class="shimmer-line short"></div>
      <div class="muted small center">Processing transcription…</div>
    </div>

    <div v-if="video && isPipelineDone" class="section">
      <h2>Summary</h2>
      <div v-if="!video.summary" class="muted">No summary yet.</div>
      <div v-else class="md" v-html="renderedSummary"></div>
      <div class="actions">
        <button class="btn" :disabled="aiLoading" @click="summarizeWithAI">
          {{ aiLoading ? 'Summarizing…' : 'Refresh summary' }}
        </button>
        <p v-if="aiError" class="error">{{ aiError }}</p>
      </div>
    </div>

    <div v-if="video && isPipelineDone" class="section">
      <h2>
        Transcription
        <button class="btn small" @click="showTranscribe = !showTranscribe">
          {{ showTranscribe ? 'Hide' : 'Show' }}
        </button>
      </h2>

      <div v-if="showTranscribe">
        <div v-if="!editing" class="transcribe-box">
          <pre class="pre">{{ video.transcribe || 'No transcription yet.' }}</pre>
          <div class="actions">
            <button class="btn" @click="editing = true">Edit</button>
            <button class="btn" @click="clearTranscribe" :disabled="!video.transcribe">Clear</button>
          </div>
        </div>
        <div v-else class="transcribe-box">
          <textarea v-model="editTranscribe" class="textarea" rows="12" placeholder="Edit transcription..."></textarea>
          <div class="actions">
            <button class="btn primary" @click="saveTranscribe">Save</button>
            <button class="btn" @click="editing=false; editTranscribe = video.transcribe || ''">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.page {
  max-width: 880px;
  margin: 0 auto;
  padding: 32px 20px;
  color: var(--text);
}
h1 { margin-bottom: 1rem; }
h2 { margin: 1.618rem 0 0.618rem; font-size: 1.25rem; }

.muted { color: var(--muted); }
.error { color: var(--red); }
.link-url {
  color: #ccc;
  text-decoration: none;
  font-weight: 500;
}
.link-url:hover { text-decoration: underline; }

/* Back button (updated to match theme) */
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

/* Card design */
.card {
  background: #222;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1.618rem;
  margin-bottom: 1.618rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.2);
}
.row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 0.618rem;
  align-items: center;
  font-size: 0.95rem;
}
.label { color: #888; font-size: 0.85rem; }

.section {
  background: #1d1d1d;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1.618rem;
  margin-top: 1.618rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.2);
}

/* Transcription */
.transcribe-box { margin-top: 0.618rem; }
.pre {
  background: #111;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 12px;
  white-space: pre-wrap;
  color: #ccc;
  line-height: 1.45;
}
.textarea {
  width: 100%;
  background: #111;
  border: 1px solid #333;
  border-radius: 8px;
  color: #ddd;
  padding: 10px 12px;
  font-family: ui-monospace, monospace;
}
.textarea:focus { outline: 1px solid #555; }

/* Buttons */
.actions { display: flex; gap: 0.618rem; margin-top: 0.618rem; }
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
.btn:hover { background: #555; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn.small { padding: 6px 10px; font-size: 14px; }
.btn.primary { background: #555; border-color: #666; }

/* Loading shimmer */
.loading-card {
  background: #1d1d1d;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1.618rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.2);
  margin-top: 1.618rem;
}
.shimmer-line {
  height: 10px;
  border-radius: 6px;
  background: linear-gradient(90deg, #2a2a2a 0%, #323232 50%, #2a2a2a 100%);
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite;
  margin-bottom: 0.618rem;
}
.shimmer-line.title { height: 16px; width: 60%; }
.shimmer-line.short { width: 40%; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* Markdown */
.md h1, .md h2, .md h3, .md h4 { margin-top: 1rem; }
.md p, .md ul { margin-bottom: 0.5rem; line-height: 1.5; }
.md ul { padding-left: 1.2rem; }
</style>
