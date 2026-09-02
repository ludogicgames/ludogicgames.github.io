// Efecto de "descenso por la ciudad": mueve el marcador de la escala de
// profundidad y da paralaje sutil a las fachadas de cada planta al hacer scroll.
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

  function clamp(v, min, max) {
    return Math.max(min, Math.min(max, v));
  }

  function update() {
    const facades = document.querySelectorAll('.floor-facade');
    const viewportCenter = window.innerHeight / 2;

    facades.forEach((facade, i) => {
      const row = facade.closest('.floor-row');
      const rect = row.getBoundingClientRect();
      const rowCenter = rect.top + rect.height / 2;
      const distanceFromCenter = viewportCenter - rowCenter;
      const distance = clamp01(1 - Math.abs(distanceFromCenter) / window.innerHeight);

      // La fachada entera flota un poco (paralaje vertical)...
      const offset = distanceFromCenter * 0.06;
      facade.style.transform = `translateY(${offset.toFixed(1)}px)`;
      facade.style.opacity = (0.4 + distance * 0.6).toFixed(2);

      // ...y el mini-edificio 3D gira ligeramente hacia el visitante al
      // acercarse al centro de la pantalla, para reforzar la sensación 3D.
      const building = facade.querySelector('.building-3d');
      if (building) {
        const baseAngle = i % 2 === 0 ? -20 : 20;
        const swing = clamp(-distanceFromCenter * 0.045, -14, 14);
        building.style.transform = `rotateY(${(baseAngle + swing).toFixed(1)}deg)`;
      }
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
