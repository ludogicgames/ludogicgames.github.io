// Efecto de "descenso por la ciudad": mueve el marcador de la escala de
// profundidad y da paralaje sutil a las fachadas de cada planta al hacer scroll.
// Depende del DOM generado por render.js (se carga después en index.html).

(function () {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const gaugeTrack = document.getElementById('gauge-track');
  const gaugeMarker = document.getElementById('gauge-marker');
  const floorsSection = document.getElementById('plantas');

  function clamp01(v) {
    return Math.max(0, Math.min(1, v));
  }

  function update() {
    const facades = document.querySelectorAll('.floor-facade');
    const viewportCenter = window.innerHeight / 2;

    facades.forEach((facade) => {
      const row = facade.closest('.floor-row');
      const rect = row.getBoundingClientRect();
      const rowCenter = rect.top + rect.height / 2;
      const distance = clamp01(1 - Math.abs(viewportCenter - rowCenter) / window.innerHeight);
      const offset = (viewportCenter - rowCenter) * 0.06;
      facade.style.transform = `translateY(${offset.toFixed(1)}px)`;
      facade.style.opacity = (0.35 + distance * 0.65).toFixed(2);
    });

    if (gaugeTrack && gaugeMarker && floorsSection) {
      const rect = floorsSection.getBoundingClientRect();
      const total = rect.height - window.innerHeight;
      const scrolled = clamp01(total > 0 ? -rect.top / total : 0);
      gaugeMarker.style.top = `${(scrolled * 100).toFixed(2)}%`;
    }
  }

  let ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      update();
      ticking = false;
    });
  }

  // render.js (cargado antes, con defer) ya ha generado el DOM para cuando
  // este script se ejecuta, así que no hace falta esperar a ningún evento.
  update();
  if (!reducedMotion) {
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
  }
})();
