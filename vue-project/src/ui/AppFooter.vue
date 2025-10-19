<script setup></script>

<template>
  <footer class="footer">
    <div class="inner">
      <!-- Left links -->
      <div class="links">
        <a href="/terms">Terms</a>
        <a href="/privacy">Privacy</a>
        <a href="/cookies">Cookies</a>
      </div>

      <!-- Center text -->
      <p class="muted small center">
        InsightFeed © {{ new Date().getFullYear() }}. All rights reserved.
      </p>

      <!-- Right button -->
      <button class="btn admin">Admin Panel</button>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100vw;
  z-index: 50;
  border-top: 1px solid var(--border);
  background: color-mix(in srgb, var(--panel) 90%, transparent);
  backdrop-filter: blur(10px) saturate(130%);
  height: 26px; /* shorter than topbar */
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

/* Full-width layout consistent with topbar */
.inner {
  width: 100%;
  max-width: 100vw;
  padding: 0 1.618rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  font-size: 12px;
  box-sizing: border-box;
}

/* Left links */
.links {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.links a {
  color: var(--muted);
  text-decoration: none;
  font-size: 12px;
  transition: color 0.2s ease;
}
.links a:hover {
  color: var(--text);
}

/* Center text */
.center {
  flex: 1;
  text-align: center;
  color: var(--muted);
  white-space: nowrap;
}

/* Right button */
.btn.admin {
  background: #b51d1d;
  border: 1px solid #b51d1d;
  color: #fff;
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  flex-shrink: 0;
}
.btn.admin:hover {
  background: #c73232;
  border-color: #c73232;
  box-shadow: 0 0 8px rgba(197, 50, 50, 0.4);
}

/* Responsive */
@media (max-width: 720px) {
  .footer {
    height: auto;
    padding: 6px 0;
  }

  .inner {
    flex-direction: column;
    gap: 4px;
    text-align: center;
    padding: 0.5rem;
  }

  .links {
    order: 1;
    justify-content: center;
  }

  .center {
    order: 2;
    white-space: normal;
  }

  .btn.admin {
    order: 3;
    padding: 4px 12px;
  }
}
</style>
