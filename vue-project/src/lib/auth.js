import { reactive } from 'vue'

const rawBase = import.meta.env?.VITE_API_BASE || import.meta.env?.VITE_API_BASE_URL
const API_BASE = (rawBase && !/:(5173|3000)(\/|$)/.test(rawBase)) ? rawBase : 'http://localhost:5000'
const GOOGLE_CLIENT_ID = import.meta.env?.VITE_GOOGLE_CLIENT_ID

export const authState = reactive({
  token: null,
  user: null,
  ready: false,
})

function save() {
  if (authState.token) localStorage.setItem('token', authState.token)
  else localStorage.removeItem('token')
}

export async function authFetch(path, options = {}) {
  const headers = new Headers(options.headers || {})
  headers.set('Content-Type', 'application/json')
  if (authState.token) headers.set('Authorization', `Bearer ${authState.token}`)
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const msg = data?.error || res.statusText
    throw new Error(msg)
  }
  return data
}

export async function initAuth() {
  const token = localStorage.getItem('token')
  if (token) {
    authState.token = token
    try {
      const { user } = await authFetch('/auth/me')
      authState.user = user
    } catch (_) {
      authState.token = null
      save()
    }
  }
  authState.ready = true
}

export async function signIn(email, password) {
  const { token, user } = await authFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  authState.token = token
  authState.user = user
  save()
  return user
}

export async function signUp(name, email, password) {
  const { token, user } = await authFetch('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  })
  authState.token = token
  authState.user = user
  save()
  return user
}

export function signOut() {
  authState.token = null
  authState.user = null
  save()
}

function ensureGoogleScript() {
  return new Promise((resolve) => {
    if (window.google && window.google.accounts && window.google.accounts.id) return resolve()
    const check = () => {
      if (window.google && window.google.accounts && window.google.accounts.id) resolve()
      else setTimeout(check, 50)
    }
    check()
  })
}

export async function signInWithGoogle() {
  if (!GOOGLE_CLIENT_ID) throw new Error('Missing VITE_GOOGLE_CLIENT_ID')
  await ensureGoogleScript()
  return new Promise((resolve, reject) => {
    try {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response) => {
          try {
            const { token, user } = await authFetch('/auth/google', {
              method: 'POST',
              body: JSON.stringify({ id_token: response.credential }),
            })
            authState.token = token
            authState.user = user
            save()
            resolve(user)
          } catch (e) {
            reject(e)
          }
        },
      })
      window.google.accounts.id.prompt((notif) => {
        if (notif && notif.isNotDisplayed()) {
          reject(new Error('Google prompt not displayed'))
        }
      })
    } catch (e) {
      reject(e)
    }
  })
}

export async function renderGoogleButton(container, onSuccess) {
  if (!container) return false
  if (!GOOGLE_CLIENT_ID) return false
  await ensureGoogleScript()
  const callback = async (response) => {
    try {
      const { token, user } = await authFetch('/auth/google', {
        method: 'POST',
        body: JSON.stringify({ id_token: response.credential }),
      })
      authState.token = token
      authState.user = user
      save()
      if (typeof onSuccess === 'function') onSuccess(user)
    } catch (e) {
      console.error('Google sign-in failed', e)
    }
  }
  window.google.accounts.id.initialize({ client_id: GOOGLE_CLIENT_ID, callback })
  try {
    window.google.accounts.id.renderButton(container, {
      theme: 'outline',
      size: 'large',
      text: 'continue_with',
      shape: 'pill',
      width: 280,
      logo_alignment: 'left',
    })
  } catch (e) {
    console.warn('renderButton failed; falling back to prompt', e)
    window.google.accounts.id.prompt()
  }
  return true
}
