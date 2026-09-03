// Efecto "rayos X de ascensor": cada planta se inclina en 3D según su
// posición en pantalla (suelo al entrar por abajo, de frente en el centro,
// techo al salir por arriba), y la cabina del ascensor + el indicador de
// planta se mueven acorde. Depende del DOM generado por render.js.

(function () {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const cabin = document.getElementById('elevator-cabin');
  const readout = document.getElementById('elevator-readout');
  const floorsSection = document.getElementById('plantas');

  function clamp01(v) {
    return Math.max(0, Math.min(1, v));
  }

  function clamp(v, min, max) {
    return Math.max(min, Math.min(max, v));
  }

  function update() {
    const viewportCenter = window.innerHeight / 2;
    let nearestCode = null;
    let nearestDistance = Infinity;

    document.querySelectorAll('.floor-row').forEach((row) => {
      const card = row.querySelector('.floor-card');
      if (!card) return;

      const rect = row.getBoundingClientRect();
      const rowCenter = rect.top + rect.height / 2;
      const distanceFromCenter = viewportCenter - rowCenter;

      // Rayos X: entrando por abajo (distancia positiva) se ve el suelo,
      // saliendo por arriba (distancia negativa) se ve el techo.
      const tilt = clamp(-distanceFromCenter * 0.1, -58, 58);
      card.style.transform = `rotateX(${tilt.toFixed(1)}deg)`;

      const absDistance = Math.abs(distanceFromCenter);
      if (absDistance < nearestDistance) {
        nearestDistance = absDistance;
        nearestCode = row.dataset.code;
      }
    });

    if (readout && nearestCode) {
      readout.textContent = nearestCode;
    }

    if (cabin && floorsSection) {
      const rect = floorsSection.getBoundingClientRect();
      const total = rect.height - window.innerHeight;
      const scrolled = clamp01(total > 0 ? -rect.top / total : 0);
      cabin.style.top = `${(scrolled * 100).toFixed(2)}%`;
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
