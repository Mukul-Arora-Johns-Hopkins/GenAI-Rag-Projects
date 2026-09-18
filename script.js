/* Portfolio — small interactive enhancements */
document.addEventListener('DOMContentLoaded', () => {
  // Reveal sections with subtle scroll-in (progressive enhancement)
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.opacity = '1';
        e.target.style.transform = 'translateY(0)';
      }
    });
  }, { threshold: 0.08 });

  document.querySelectorAll('section > *:not(h2)').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(6px)';
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    observer.observe(el);
  });

  // Smooth anchor scrolling
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // Console greeting
  console.log(
    '%c📚 GenAI & RAG Projects — Mukul Arora',
    'font-size:13px; font-weight:600; color:#8c6a3e;'
  );
  console.log(
    '%cBuilt with Ollama · sentence-transformers · Chroma · FastAPI · 100% local, no API keys.',
    'font-size:11px; color:#8a7d6a;'
  );
});
