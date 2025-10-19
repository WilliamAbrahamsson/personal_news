<script setup>
import { ref, onMounted, watch } from 'vue'
import { authState, authFetch } from '../lib/auth'

const loading = ref(false)
const error = ref('')
const sources = ref([])

async function load() {
  if (!authState.user) { sources.value = []; return }
  loading.value = true
  error.value = ''
  try {
    sources.value = await authFetch('/sources')
  } catch (e) {
    error.value = e.message || 'Failed to load sources'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => authState.user, load)
</script>

<template>
  <section class="page">
    <div class="head">
      <h1>Sources</h1>
      <router-link v-if="authState.user" to="/add" class="btn primary">Add Source</router-link>
    </div>

    <p v-if="!authState.user" class="muted center">Please sign in to see your sources.</p>
    <p v-else-if="loading" class="muted center">Loading…</p>
    <p v-else-if="error" class="error center">{{ error }}</p>

    <ul v-else class="grid">
      <li v-for="s in sources" :key="s.id">
        <router-link :to="`/sources/${s.id}`" class="card-link">
          <div class="card">
            <div class="top-row">
              <span class="badge" :data-type="s.type">
                {{ s.type === 'youtube_channel' ? 'YouTube Channel' : s.type }}
              </span>
            </div>
            <h2 class="title">{{ s.label || s.value }}</h2>
            <p class="muted small mono">{{ s.value }}</p>
            <p class="added small muted">Added {{ new Date(s.created_at).toLocaleString() }}</p>
          </div>
        </router-link>
      </li>
    </ul>
  </section>
</template>

<style scoped>
/* === Layout rhythm === */
.page {
  max-width: 960px;
  margin: 0 auto;
  padding: 2.618rem 1.618rem;
  color: var(--text);
  line-height: 1.618;
}
.center { text-align: center; }
.muted { color: var(--muted); }
.small { font-size: 0.9rem; }
.mono { font-family: ui-monospace, monospace; word-break: break-all; }
.error { color: var(--red); }

/* === Header === */
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2.618rem;
}
h1 {
  margin: 0;
  font-size: 1.618rem;
  letter-spacing: -0.01em;
  font-weight: 700;
}

/* === Grid === */
.grid {
  display: grid;
  gap: 1.618rem;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  list-style: none;
  padding: 0;
  margin: 0;
}

/* === Card link === */
.card-link {
  display: block;
  text-decoration: none;
  color: inherit;
  transition: transform 0.3s cubic-bezier(0.33, 1, 0.68, 1),
              box-shadow 0.3s ease,
              border-color 0.2s ease;
}
.card-link:hover .card {
  transform: translateY(-3px);
  border-color: #555;
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.25);
}

/* === Card === */
.card {
  background: #1c1c1c;
  border: 1px solid #2f2f2f;
  border-radius: 10px;
  padding: 1.618rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  gap: 0.618rem;
  height: 100%;
  overflow-wrap: break-word;
  word-break: break-word;
  transition: border-color 0.2s ease;
}

/* === Card structure === */
.top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* === Badge === */
.badge {
  display: inline-block;
  font-size: 0.8rem;
  padding: 0.236rem 0.618rem;
  border-radius: 999px;
  background: #2b2b2b;
  border: 1px solid #3a3a3a;
  color: #bbb;
  font-weight: 500;
  white-space: nowrap;
  line-height: 1.2;
}
.badge[data-type="youtube_channel"] {
  color: #c4302b;
}

/* === Title & Content === */
.title {
  color: #eee;
  font-weight: 600;
  font-size: 1.1rem;
  line-height: 1.35;
  margin: 0.382rem 0 0.236rem;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.mono {
  color: #aaa;
  font-size: 0.85rem;
  opacity: 0.9;
}
.added {
  margin-top: 0.382rem;
  opacity: 0.7;
  font-size: 0.8rem;
}

/* === Button === */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.382rem;
  padding: 0.618rem 1rem;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  color: #ddd;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}
.btn:hover {
  background: #333;
  border-color: #555;
  color: #fff;
  transform: translateY(-1px);
}
.btn:active {
  background: #3a3a3a;
  transform: translateY(0);
}
.btn.primary {
  background: #444;
  border-color: #555;
}
.btn.primary:hover {
  background: #555;
  border-color: #666;
}
</style>
