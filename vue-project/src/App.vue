<script setup>
import TopBar from './ui/TopBar.vue'
import AppFooter from './ui/AppFooter.vue'
</script>

<template>
  <div class="app-shell">
    <TopBar />
    <main class="app-content">
      <router-view />
    </main>
    <AppFooter />
  </div>
  
</template>

<style>
:root {
  --bg: #1C1C1C;        /* Dark gray 1 */
  --panel: #272725;     /* Dark gray 2 */
  --text: #E3E3E3;      /* White */
  --muted: #E3E3E3;     /* Use opacity for muted visuals */
  --accent: #0B8CE9;    /* Blue */
  --red: #F14E1E;       /* Red */
  --green: #0BD185;     /* Green */
  --border: #272725;    /* Dark gray border */
}

html, body, #app {
  height: 100%;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, Noto Sans,
    "Apple Color Emoji", "Segoe UI Emoji";
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-shell {
  min-height: 100%;
  display: grid;
  grid-template-rows: auto 1fr auto;
}

.app-content {
  width: min(1100px, 92%);
  margin: 56px auto 24px; /* header offset (smaller topbar) */
}

a {
  color: var(--accent);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

.muted { opacity: 0.7; }

/* Global button defaults */
.btn { border-radius: 5px; font-size: 13px; }
</style>
