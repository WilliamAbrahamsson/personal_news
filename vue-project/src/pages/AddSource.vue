<script setup>
import { ref, computed } from 'vue'
import { authState, authFetch } from '../lib/auth'

const options = [
  { key: 'youtube_channel', label: 'YouTube Channel', enabled: true },
  { key: 'rss_feed', label: 'RSS Feed', enabled: false },
  { key: 'twitter_account', label: 'Twitter Account', enabled: false },
  { key: 'reddit_sub', label: 'Reddit Subreddit', enabled: false },
]

const selected = ref('youtube_channel')
const url = ref('')
const message = ref('')
const error = ref('')
const loading = ref(false)

const canSubmit = computed(() => authState.user && selected.value === 'youtube_channel' && url.value.trim().length > 0)

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  message.value = ''
  error.value = ''
  try {
    const res = await authFetch('/sources', {
      method: 'POST',
      body: JSON.stringify({ type: selected.value, value: url.value }),
    })
    message.value = '✅ Source added successfully.'
    url.value = ''
  } catch (e) {
    error.value = e.message || 'Failed to add source'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="page">
    <h1 class="page-title">Add News Source</h1>
    <p class="muted intro">Choose a source type to follow. Only YouTube is available for now.</p>

    <div class="options">
      <button
        v-for="opt in options"
        :key="opt.key"
        class="opt"
        :data-selected="selected === opt.key"
        :disabled="!opt.enabled"
        @click="selected = opt.key"
        :title="opt.enabled ? '' : 'Coming soon'"
      >
        {{ opt.label }}
      </button>
    </div>

    <div v-if="!authState.user" class="notice">Please sign in to add a source.</div>

    <form class="form-card" @submit.prevent="submit">
      <div class="field">
        <label>YouTube Channel URL or ID</label>
        <input
          v-model="url"
          placeholder="https://youtube.com/@veritasium"
          :disabled="!authState.user || selected !== 'youtube_channel'"
        />
      </div>

      <button class="btn primary" type="submit" :disabled="!canSubmit || loading">
        {{ loading ? 'Adding…' : 'Add Source' }}
      </button>

      <p v-if="message" class="ok">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
  </section>
</template>

<style scoped>
/* Layout */
.page {
  max-width: 640px;
  margin: 0 auto;
  padding: 2.618rem 1.618rem;
  color: var(--text);
}
.page-title {
  font-size: 1.9rem;
  font-weight: 700;
  margin-bottom: 0.618rem;
}
.intro {
  font-size: 0.95rem;
  margin-bottom: 1.618rem;
}
.muted {
  color: var(--muted);
}

/* Option selector */
.options {
  display: flex;
  flex-wrap: wrap;
  gap: 0.618rem;
  margin-bottom: 1.618rem;
}
.opt {
  padding: 0.618rem 1rem;
  border-radius: 999px;
  border: 1px solid #3a3a3a;
  background: #1d1d1d;
  color: #ccc;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
}
.opt:hover:not(:disabled) {
  background: #2a2a2a;
  color: #fff;
  border-color: #555;
}
.opt[data-selected="true"] {
  background: #333;
  border-color: #666;
  color: #fff;
  box-shadow: 0 0 10px rgba(255,255,255,0.06);
}
.opt:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Form Card */
.form-card {
  background: #1d1d1d;
  border: 1px solid #333;
  border-radius: 12px;
  padding: 1.618rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  display: flex;
  flex-direction: column;
  gap: 1.618rem;
  transition: all 0.3s ease;
}
.form-card:hover {
  transform: translateY(-2px);
  border-color: #555;
  box-shadow: 0 6px 12px rgba(0,0,0,0.3);
}

/* Field */
.field {
  display: flex;
  flex-direction: column;
  gap: 0.618rem;
}
.field label {
  font-size: 0.9rem;
  color: var(--muted);
}
.field input {
  background: #111;
  color: #ddd;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  font-size: 0.95rem;
  transition: all 0.2s ease;
}
.field input:focus {
  outline: none;
  border-color: #555;
  background: #151515;
}

/* Button */
.btn {
  background: #444;
  color: #eee;
  border: 1px solid #555;
  border-radius: 8px;
  padding: 0.618rem 1.2rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn.primary {
  background: #3a3a3a;
  border-color: #555;
}
.btn.primary:hover {
  background: #555;
  border-color: #666;
  color: #fff;
}
.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Feedback */
.ok {
  color: var(--green);
  font-size: 0.9rem;
  margin: -0.5rem 0 0;
}
.error {
  color: var(--red);
  font-size: 0.9rem;
  margin: -0.5rem 0 0;
}

/* Sign-in notice */
.notice {
  background: #222;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1rem;
  margin-bottom: 1.618rem;
  color: var(--muted);
  font-size: 0.95rem;
  box-shadow: inset 0 0 8px rgba(0,0,0,0.2);
}
</style>
