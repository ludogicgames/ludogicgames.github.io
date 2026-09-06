// Partículas ambientales (burbujas blanco/rojo, el acento de marca) de
// fondo para toda la web, no solo el hero — un único canvas 2D fijo,
// ligero, independiente de la escena 3D de la puerta (hero3d.js).
// Respeta prefers-reduced-motion.

(function () {
  const canvas = document.getElementById('ambient-particles');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const COLORS = ['rgba(244,248,251,ALPHA)', 'rgba(232,154,154,ALPHA)', 'rgba(216,78,78,ALPHA)'];

  let w = 0;
  let h = 0;
  let particles = [];

  function makeParticle() {
    return {
      x: Math.random() * w,
      y: Math.random() * h,
      r: Math.random() * 1.8 + 0.6,
      speed: Math.random() * 0.18 + 0.05,
      drift: (Math.random() - 0.5) * 0.12,
      alpha: Math.random() * 0.35 + 0.12,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
    };
  }

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
    const count = Math.min(90, Math.floor((w * h) / 22000));
    particles = Array.from({ length: count }, makeParticle);
  }

  function drawFrame() {
    ctx.clearRect(0, 0, w, h);
    particles.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.color.replace('ALPHA', p.alpha.toFixed(2));
      ctx.fill();
    });
  }

  function tick() {
    particles.forEach((p) => {
      p.y -= p.speed;
      p.x += p.drift;
      if (p.y < -4) {
        p.y = h + 4;
        p.x = Math.random() * w;
      }
      if (p.x < -4) p.x = w + 4;
      if (p.x > w + 4) p.x = -4;
    });
    drawFrame();
    requestAnimationFrame(tick);
  }

  resize();
  window.addEventListener('resize', () => {
    resize();
    if (reducedMotion) drawFrame();
  });

  if (reducedMotion) {
    drawFrame();
  } else {
    tick();
  }
})();
