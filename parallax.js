// Efecto de "ascensor": mueve el marcador de la escala de profundidad y
// oscurece el techo/suelo de cada planta según su distancia al centro de
// la pantalla, como si solo la planta actual estuviera iluminada.
// Depende del DOM generado por render.js (se carga después en index.html).

(function () {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const gaugeTrack = document.getElementById('gauge-track');
  const gaugeMarker = document.getElementById('gauge-marker');
  const floorsSection = document.getElementById('plantas');
  const skylineFar = document.querySelector('.skyline-far');
  const skylineMid = document.querySelector('.skyline-mid');

  function clamp01(v) {
    return Math.max(0, Math.min(1, v));
  }

  function update() {
    const cells = document.querySelectorAll('.floor-cell');
    const viewportCenter = window.innerHeight / 2;

    cells.forEach((cell) => {
      const row = cell.closest('.floor-row');
      const rect = row.getBoundingClientRect();
      const rowCenter = rect.top + rect.height / 2;
      const distanceFromCenter = viewportCenter - rowCenter;
      const distance = clamp01(1 - Math.abs(distanceFromCenter) / window.innerHeight);

      // Techo y suelo se oscurecen cuando la planta no está cerca del
      // centro de la pantalla, como si solo la planta actual estuviera
      // iluminada dentro del hueco del ascensor.
      const glow = (0.2 + distance * 0.8).toFixed(2);
      cell.querySelectorAll('.shaft-plane').forEach((plane) => {
        plane.style.opacity = glow;
      });
    });

    if (gaugeTrack && gaugeMarker && floorsSection) {
      const rect = floorsSection.getBoundingClientRect();
      const total = rect.height - window.innerHeight;
      const scrolled = clamp01(total > 0 ? -rect.top / total : 0);
      gaugeMarker.style.top = `${(scrolled * 100).toFixed(2)}%`;

      // Capas de skyline al fondo, moviéndose más despacio que el contenido
      // (la lejana más despacio que la intermedia) para dar profundidad.
      const travel = rect.height * 0.6;
      if (skylineFar) skylineFar.style.backgroundPositionY = `${(scrolled * travel * 0.15).toFixed(1)}px`;
      if (skylineMid) skylineMid.style.backgroundPositionY = `${(scrolled * travel * 0.32).toFixed(1)}px`;
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
