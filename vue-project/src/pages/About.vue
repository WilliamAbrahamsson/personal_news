<script setup>
</script>

<template>
  <section class="about">
    <div class="content">
      <h1>About InsightFeed</h1>
      <p class="intro">
        InsightFeed is your personal AI-powered content companion — designed to keep you informed without the noise.
      </p>

      <p>
        It automatically gathers videos and news from your favorite sources, transcribes and summarizes them,
        and presents key takeaways in a minimal, distraction-free dashboard.
      </p>

      <p>
        Built with <strong>Vue 3</strong>, <strong>Vite</strong>, and <strong>OpenAI</strong> technologies,
        InsightFeed focuses on clarity, control, and calm consumption.
      </p>

      <div class="credit-box">
        <h2>Credits</h2>
        <ul>
          <li>Design inspired by minimal productivity tools.</li>
          <li>Powered by the OpenAI Whisper and GPT models.</li>
          <li>Frontend built with Vue 3 and modern CSS principles.</li>
        </ul>
      </div>


    </div>
  </section>
</template>

<style scoped>
.about {
  max-width: 800px;
  margin: 0 auto;
  padding: 2.618rem 1.618rem;
  background: #1d1d1d;
  border: 1px solid #333;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  color: var(--text);
  line-height: 1.7;
  display: flex;
  flex-direction: column;
  gap: 1.618rem;
  transition: all 0.3s ease;
}
.about:hover {
  transform: translateY(-2px);
  border-color: #555;
  box-shadow: 0 6px 12px rgba(0,0,0,0.3);
}

.content {
  display: flex;
  flex-direction: column;
  gap: 1.618rem;
}

h1 {
  font-size: 1.9rem;
  font-weight: 700;
  margin: 0;
  color: #eee;
}

.intro {
  font-size: 1.05rem;
  color: #ccc;
  margin: 0;
}

p {
  color: #bbb;
  font-size: 0.97rem;
  margin: 0;
}

strong {
  color: #fff;
  font-weight: 600;
}

.credit-box {
  background: #222;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1.618rem;
  box-shadow: inset 0 0 10px rgba(0,0,0,0.2);
}
.credit-box h2 {
  font-size: 1.25rem;
  margin-bottom: 0.618rem;
  color: #ddd;
}
.credit-box ul {
  list-style: disc;
  margin: 0;
  padding-left: 1.5rem;
  color: #aaa;
}
.credit-box li {
  margin-bottom: 0.5rem;
  line-height: 1.5;
}

.footer {
  border-top: 1px solid #333;
  margin-top: 1.618rem;
  padding-top: 0.618rem;
  text-align: center;
}
.muted { color: var(--muted); }
.small { font-size: 0.9rem; }

@media (max-width: 640px) {
  .about {
    padding: 1.618rem 1rem;
  }
  h1 { font-size: 1.6rem; }
}
</style>
