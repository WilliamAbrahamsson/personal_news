<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { authState, authFetch } from '../lib/auth'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const videos = ref([])
const sources = ref([])
const selectedSources = ref([])

/* --- Markdown rendering --- */
function mdToHtml(md) {
  let esc = (s) =>
    s.replace(/&/g, '&amp;')
     .replace(/</g, '&lt;')
     .replace(/>/g, '&gt;')
  md = esc(md || '')
  md = md.replace(/^######\s+(.*)$/gm, '<h6>$1</h6>')
          .replace(/^#####\s+(.*)$/gm, '<h5>$1</h5>')
          .replace(/^####\s+(.*)$/gm, '<h4>$1</h4>')
          .replace(/^###\s+(.*)$/gm, '<h3>$1</h3>')
          .replace(/^##\s+(.*)$/gm, '<h2>$1</h2>')
          .replace(/^#\s+(.*)$/gm, '<h1>$1</h1>')
  md = md.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*(.+?)\*/g, '<em>$1</em>')
  md = md.replace(/(^|\n)(-\s.+(?:\n-\s.+)*)/g, (m, p1, block) => {
    const items = block.split(/\n/).map(l => l.replace(/^-\s+/, '')).map(li => `<li>${li}</li>`).join('')
    return `${p1}<ul>${items}</ul>`
  })
  md = md.replace(/\n{2,}/g, '</p><p>')
  md = `<p>${md}</p>`
  return md
}
function renderSummary(v) { return mdToHtml(v.summary) }

/* --- Load all data --- */
async function load() {
  if (!authState.user) { videos.value = []; sources.value = []; return }
  loading.value = true
  error.value = ''
  try {
    const [srcs, vids] = await Promise.all([
      authFetch('/sources'),
      authFetch('/videos'),
    ])
    sources.value = srcs
    videos.value = vids
  } catch (e) {
    error.value = e.message || 'Failed to load data'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => authState.user, load)

/* --- Filtering logic --- */
function toggleSource(id) {
  if (selectedSources.value.includes(id)) {
    selectedSources.value = selectedSources.value.filter(s => s !== id)
  } else {
    selectedSources.value.push(id)
  }
}
function clearFilter(id) {
  selectedSources.value = selectedSources.value.filter(s => s !== id)
}

const filteredVideos = computed(() => {
  if (!selectedSources.value.length) return videos.value
  return videos.value.filter(v => selectedSources.value.includes(v.source_id))
})
</script>

<template>
  <section class="page">
    <h1 class="page-title">Dashboard</h1>

    <p v-if="!authState.user" class="muted center">Please sign in to see your summaries.</p>
    <p v-else-if="loading" class="muted center">Loading…</p>
    <p v-else-if="error" class="error center">{{ error }}</p>

    <!-- Filter row -->
    <div v-else class="filter-row">
      <div class="filter-list">
        <button
          v-for="s in sources"
          :key="s.id"
          class="chip"
          :class="{ active: selectedSources.includes(s.id) }"
          @click="toggleSource(s.id)"
        >
          {{ s.label || s.value }}
          <span
            v-if="selectedSources.includes(s.id)"
            class="x"
            @click.stop="clearFilter(s.id)"
          >×</span>
        </button>
      </div>

      <button class="btn-add" @click="router.push('/add')">Add new source</button>
    </div>

    <!-- Video cards -->
    <ul v-if="authState.user && !loading && !error" class="list">
      <li
        v-for="v in filteredVideos"
        :key="v.id"
        class="card"
        :class="{ 'loading-card': !v.summary }"
      >
        <div class="head">
          <router-link
            class="title"
            :to="`/sources/${v.source_id}/videos/${v.id}`"
          >
            {{ v.title || v.url }}
          </router-link>

          <a
            class="btn youtube"
            :href="v.url"
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              width="16"
              height="16"
            >
              <path
                fill="currentColor"
                d="M23.5 6.2s-.2-1.6-.8-2.3c-.8-.8-1.7-.8-2.1-.9C17.9 2.6 12 2.6 12 2.6s-5.9 0-8.6.4c-.4 0-1.4.1-2.1.9C.7 4.6.5 6.2.5 6.2S.2 8.2.2 10.3v1.9c0 2.1.3 4.1.3 4.1s.2 1.6.8 2.3c.8.8 1.9.8 2.4.9 1.7.2 7.3.4 7.3.4s5.9 0 8.6-.4c.4 0 1.4-.1 2.1-.9.6-.7.8-2.3.8-2.3s.3-2 .3-4.1v-1.9c0-2.1-.3-4.1-.3-4.1zM9.7 13.9V7.9l6.2 3-6.2 3z"
              />
            </svg>
            Open
          </a>
        </div>

        <div
          v-if="v.summary"
          class="summary md"
          v-html="renderSummary(v)"
        ></div>

        <div v-else class="skeleton">
          <div class="skeleton-line short"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-line long"></div>
          <div class="skeleton-line"></div>
        </div>

        <div class="meta muted small">
          Added {{ new Date(v.created_at).toLocaleString() }}
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.page {
  max-width: 960px;
  margin: 0 auto;
  padding: 0.4rem 1.618rem 1.4rem; /* tighter top & bottom spacing */
  color: var(--text);
}

.center { text-align: center; }
.muted { color: var(--muted); }
.error { color: var(--red); }
.small { font-size: 13px; }

.page-title {
  font-size: 1.9rem;
  font-weight: 700;
  margin-bottom: 0.6rem; /* less space under title */
}

/* --- Filter row --- */
.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.filter-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

/* --- Chips --- */
.chip {
  background: #1f1f1f;
  color: #ccc;
  border: 1px solid #333;
  border-radius: 999px;
  padding: 4px 10px 4px 12px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: all 0.25s ease;
}
.chip:hover {
  background: #292929;
  border-color: #444;
  color: #eee;
}
.chip.active {
  background: #4c6ef5;
  border-color: #4c6ef5;
  color: #fff;
}
.x {
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
  opacity: 0.85;
}
.x:hover { opacity: 0.65; }

/* --- Add new source button (gray) --- */
.btn-add {
  background: #2b2b2b;
  border: 1px solid #3a3a3a;
  color: #ddd;
  font-weight: 600;
  font-size: 13px;
  padding: 5px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.25s ease;
}
.btn-add:hover {
  background: #3a3a3a;
  border-color: #555;
  color: #fff;
  transform: translateY(-1px);
}

/* --- Cards --- */
.list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 1.618rem;
}

.card {
  background: #1d1d1d;
  border: 1px solid #333;
  border-radius: 12px;
  padding: 1.618rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  transition: all 0.25s ease;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.card:hover {
  transform: translateY(-3px);
  border-color: #555;
  box-shadow: 0 6px 14px rgba(0,0,0,0.35);
}

/* --- Header --- */
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 0.618rem;
}
.title {
  flex: 1;
  color: #eee;
  font-weight: 600;
  font-size: 1.05rem;
  line-height: 1.35;
  text-decoration: none;
  word-break: break-word;
}
.title:hover {
  color: #fff;
  text-decoration: underline;
}

/* --- Markdown summary --- */
.md {
  color: #ccc;
  font-size: 0.95rem;
  line-height: 1.6;
}
.md :is(h1,h2,h3,h4,h5,h6) {
  color: #eee;
  margin: 0.75rem 0 0.4rem;
  font-weight: 600;
  line-height: 1.3;
}
.md p { margin: 0.5rem 0; }
.md ul {
  margin: 0.5rem 0 0.5rem 1.2rem;
  padding: 0;
  list-style: disc;
}

/* --- Meta --- */
.meta {
  margin-top: 0.25rem;
  font-size: 0.85rem;
  color: #888;
}

/* --- Buttons --- */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 13px;
  border-radius: 8px;
  border: 1px solid #3a3a3a;
  padding: 6px 12px;
  text-decoration: none;
  color: #ddd;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn:hover {
  background: #333;
  border-color: #555;
  color: #fff;
}
.btn.youtube {
  background: #c4302b;
  border-color: #a32a24;
  color: #fff;
}
.btn.youtube:hover {
  background: #e2372f;
  border-color: #e2372f;
}

/* --- Skeleton loader --- */
.skeleton {
  display: grid;
  gap: 0.5rem;
}
.skeleton-line {
  height: 14px;
  border-radius: 6px;
  background: linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 37%, #2a2a2a 63%);
  background-size: 400% 100%;
  animation: shimmer 1.4s ease infinite;
  opacity: 0.8;
}
.skeleton-line.short { width: 40%; height: 12px; }
.skeleton-line.long { width: 90%; }

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.loading-card {
  position: relative;
  overflow: hidden;
}
.loading-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%);
  animation: cardShimmer 1.8s linear infinite;
  pointer-events: none;
}
@keyframes cardShimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
</style>
