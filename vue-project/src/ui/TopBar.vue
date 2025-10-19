<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { authState, signIn, signUp, signOut, renderGoogleButton } from '../lib/auth'

const authOpen = ref(false)
const mode = ref('signin')
const name = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const googleBtn = ref(null)
const userMenuOpen = ref(false)

function resetForm() {
  name.value = ''
  email.value = ''
  password.value = ''
  error.value = ''
}

async function handleSubmit() {
  loading.value = true
  error.value = ''
  try {
    if (mode.value === 'signin') await signIn(email.value, password.value)
    else await signUp(name.value, email.value, password.value)
    authOpen.value = false
    resetForm()
  } catch (e) {
    error.value = e.message || 'Failed to authenticate'
  } finally {
    loading.value = false
  }
}

watch(authOpen, async (open) => {
  if (open) {
    await nextTick()
    if (googleBtn && googleBtn.value) {
      try { await renderGoogleButton(googleBtn.value, () => (authOpen.value = false)) } catch {}
    }
  }
})

function getUserColor(name = '', id = '') {
  const seed = (name + id).split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  const hue = seed % 360
  return `hsl(${hue}, 60%, 50%)`
}

function handleClickOutside(e) {
  if (!e.target.closest('.user-container')) userMenuOpen.value = false
}
onMounted(() => document.addEventListener('click', handleClickOutside))
onBeforeUnmount(() => document.removeEventListener('click', handleClickOutside))
</script>

<template>
  <header class="topbar">
    <nav class="nav">
      <!-- Left side -->
      <div class="left-links">
        <router-link class="brand" to="/">
          <span class="logo-box">I</span>
          <span class="brand-name">InsightFeed</span>
        </router-link>

        <router-link to="/" class="nav-link">Dash</router-link>
        <router-link to="/sources" class="nav-link">Sources</router-link>
        <router-link to="/about" class="nav-link">About</router-link>
      </div>

      <!-- Right side -->
      <div class="right-controls">
        <div class="token-box">Tokens: 2.4k</div>
        <button class="btn demo">Demo Access</button>

        <template v-if="authState.user">
          <div class="user-container">
            <button
              class="user-btn"
              :style="{ backgroundColor: getUserColor(authState.user.name, authState.user.id) }"
              @click.stop="userMenuOpen = !userMenuOpen"
            >
              {{ authState.user.name?.charAt(0)?.toUpperCase() || '?' }}
            </button>

            <transition name="fade">
              <div v-if="userMenuOpen" class="user-menu" @click.stop>
                <button class="menu-item">Settings</button>
                <button class="menu-item" @click="signOut">Log out</button>
              </div>
            </transition>
          </div>
        </template>

        <template v-else>
          <button class="btn signin" @click="authOpen = !authOpen">Sign in</button>
        </template>
      </div>

      <!-- Auth Modal -->
      <teleport to="body">
        <div v-if="authOpen && !authState.user" class="auth-overlay" @click.self="authOpen=false">
          <div class="auth-modal">
            <div class="tabs">
              <button :data-active="mode==='signin'" @click="mode='signin'">Sign in</button>
              <button :data-active="mode==='signup'" @click="mode='signup'">Sign up</button>
            </div>

            <form class="form" @submit.prevent="handleSubmit">
              <transition name="fade" mode="out-in">
                <div key="name" v-if="mode==='signup'" class="field">
                  <label>Name</label>
                  <input v-model="name" placeholder="Jane Doe" required />
                </div>
              </transition>

              <div class="field">
                <label>Email</label>
                <input v-model="email" type="email" placeholder="you@email.com" required />
              </div>

              <div class="field">
                <label>Password</label>
                <input v-model="password" type="password" placeholder="••••••••" required />
              </div>

              <p v-if="error" class="error">{{ error }}</p>

              <!-- Gray clean modal submit -->
              <button class="btn gray wide" type="submit" :disabled="loading">
                {{ loading ? 'Please wait…' : (mode==='signin' ? 'Sign in' : 'Create account') }}
              </button>

              <div class="divider"><span>or</span></div>
              <div ref="googleBtn" class="google-slot"></div>
            </form>
          </div>
        </div>
      </teleport>
    </nav>
  </header>
</template>

<style scoped>
/* Topbar layout */
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: saturate(140%) blur(8px);
  background: color-mix(in srgb, var(--panel) 82%, transparent);
  border-bottom: 1px solid var(--border);
  width: 100vw;
  left: 0;
  right: 0;
}

.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0 1.618rem;
  height: 33px;
  box-sizing: border-box;
}

/* Left links */
.left-links {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}
.nav-link {
  color: var(--muted);
  font-size: 13px;
  text-decoration: none;
  transition: color 0.2s ease;
}
.nav-link.router-link-active,
.nav-link:hover { color: var(--text); }

/* Brand */
.brand {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: var(--text);
}
.logo-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  background: var(--green);
  border-radius: 3px;
  font-weight: 800;
  font-size: 11px;
}
.brand-name { font-size: 0.95rem; }

/* Right side */
.right-controls {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  flex-shrink: 0;
}

/* Tokens + Demo */
.token-box {
  background: #1e1e1e;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 13px;
  color: #ccc;
}
.btn.demo {
  background: #444;
  border: 1px solid #555;
  color: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}
.btn.demo:hover { background: #555; }

/* Square user avatar */
.user-container { position: relative; }
.user-btn {
  width: 28px;
  height: 28px;
  border-radius: 5px;
  border: none;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  text-transform: uppercase;
  transition: transform 0.1s ease, opacity 0.2s ease;
}
.user-btn:hover { transform: scale(1.05); opacity: 0.9; }

/* Dropdown further left */
.user-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  transform: translateX(-90%);
  background: #1d1d1d;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 6px 0;
  display: flex;
  flex-direction: column;
  box-shadow: 0 6px 20px rgba(0,0,0,0.3);
  min-width: 140px;
  z-index: 50;
}
.menu-item {
  background: transparent;
  border: none;
  color: #ddd;
  padding: 8px 12px;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s;
}
.menu-item:hover { background: #2b2b2b; }

/* Sign in button (blue) */
.btn.signin {
  background: #2255ff;
  border: 1px solid #2255ff;
  color: #fff;
  border-radius: 8px;
  padding: 6px 12px;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.25s ease;
}
.btn.signin:hover {
  background: #2d63ff;
  border-color: #2d63ff;
  box-shadow: 0 0 10px rgba(34,85,255,0.35);
}

/* Gray modal button */
.btn.gray {
  background: #2a2a2a;
  border: 1px solid #444;
  color: #ddd;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.25s ease;
}
.btn.gray:hover {
  background: #333;
  border-color: #555;
  color: #fff;
}
.btn.wide { width: 100%; }

/* Fade animation */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* Auth Modal */
.auth-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: grid; place-items: center; z-index: 1000; }
.auth-modal {
  background: #1d1d1d;
  border: 1px solid #333;
  border-radius: 12px;
  padding: 2.618rem 1.618rem;
  width: min(440px, 92vw);
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
  display: flex;
  flex-direction: column;
  gap: 1.618rem;
  color: var(--text);
}
.tabs { display: flex; gap: 0.618rem; justify-content: center; }
.tabs button {
  flex: 1;
  background: #222;
  color: #999;
  border: 1px solid #333;
  padding: 0.618rem;
  border-radius: 8px;
  font-weight: 600;
}
.tabs button[data-active="true"] { background: #444; color: #fff; border-color: #555; }

.form { display: flex; flex-direction: column; gap: 1rem; }
.field { display: flex; flex-direction: column; gap: 0.382rem; }
.field label { font-size: 13px; color: #999; }
.field input {
  background: #111;
  color: #eee;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 0.75rem 1rem;
}
.field input:focus { border-color: #666; background: #151515; outline: none; }
.error { color: var(--red); font-size: 13px; margin: 0; }
.divider { display: flex; align-items: center; color: #666; font-size: 13px; }
.divider::before, .divider::after { content: ''; flex: 1; border-bottom: 1px solid #333; margin: 0 0.75em; }
.google-slot { display: grid; place-items: center; }
</style>
