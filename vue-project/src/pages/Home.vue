<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { authState, authFetch } from '../lib/auth'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const sources = ref([])

async function loadSources() {
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

function goAdd() { router.push('/add') }

onMounted(loadSources)
watch(() => authState.user, () => loadSources())
</script>

<template>
  <section class="hero">
    <h1>Personal News</h1>
    <p class="lede">
      A clean, focused feed for what matters to you.
    </p>
    <div class="cta">
      <router-link class="btn" to="/about">Learn more</router-link>
    </div>
  </section>

  <section class="panel">
    <template v-if="!authState.user">
      <h2>Welcome</h2>
      <p class="muted">Please sign in to see and manage your news sources.</p>
      <button class="btn" @click="goAdd">Add Source</button>
    </template>
    <template v-else>
      <div class="panel-head">
        <h2>Your Sources</h2>
        <button class="btn" @click="goAdd">Add Source</button>
      </div>
      <p v-if="loading" class="muted">Loading…</p>
      <p v-if="error" class="error">{{ error }}</p>
      <div v-if="!loading && sources.length === 0" class="muted">No sources yet. Click "Add Source" to get started.</div>
      <ul v-else class="sources">
        <li v-for="s in sources" :key="s.id" class="source">
          <div class="badge" :data-type="s.type">{{ s.type === 'youtube_channel' ? 'YouTube' : s.type }}</div>
          <div class="meta">
            <router-link class="label link" :to="`/sources/${s.id}`">{{ s.label || s.value }}</router-link>
            <div class="muted small">{{ s.value }}</div>
          </div>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.hero {
  margin-top: 24px;
  padding: 32px;
  border-radius: 16px;
  background: var(--panel);
  border: 1px solid var(--border);
}
h1 {
  margin: 0 0 6px 0;
  letter-spacing: -0.02em;
  font-size: 40px;
}
.lede {
  color: var(--muted);
  margin: 0 0 14px;
}
.cta { margin-top: 10px; }
.btn {
  display: inline-block;
  padding: 10px 14px;
  border-radius: 10px;
  color: var(--bg);
  background: var(--accent);
  font-weight: 600;
}
.panel {
  margin-top: 18px;
  padding: 20px;
  border-radius: 12px;
  background: var(--panel);
  border: 1px solid var(--border);
}
.muted { color: var(--muted); }

code { color: var(--accent); }

.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.sources { list-style: none; padding: 0; margin: 12px 0 0; display: grid; gap: 12px; }
.source { display: flex; gap: 12px; align-items: center; padding: 12px; border: 1px solid var(--border); border-radius: 10px; background: var(--panel); }
.badge { font-size: 12px; padding: 4px 8px; border-radius: 999px; border: 1px solid var(--border); background: var(--bg); color: var(--muted); }
.badge[data-type="youtube_channel"] { background: var(--bg); color: var(--red); border-color: var(--border); }
.meta { display: grid; gap: 2px; }
.label { font-weight: 600; }
.label.link { color: var(--text); text-decoration: none; }
.label.link:hover { text-decoration: underline; }
.small { font-size: 12px; }
.error { color: var(--red); }
</style>
