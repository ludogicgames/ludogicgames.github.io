// Botón "Hacer tour" del hero: baja la página sola, a velocidad constante
// y despacio, para que se vea todo el recorrido (puerta, edificio,
// contacto) sin que el usuario tenga que hacer scroll. Se detiene solo si
// el usuario toma el control (rueda, arrastre táctil, teclas de
// navegación) o si vuelve a pulsar el botón. Respeta prefers-reduced-motion
// devolviendo el botón inútil en vez de animar nada.

(function () {
  const btn = document.getElementById('hero-cta-tour');
  if (!btn) return;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reducedMotion) {
    btn.disabled = true;
    return;
  }

  const copy = (typeof SITE !== 'undefined' && SITE.heroCtaTour) || {};
  const START_LABEL = copy.label || 'Hacer tour';
  const STOP_LABEL = copy.stopLabel || 'Detener tour';

  const SPEED_PX_PER_SEC = 120; // recorrido cinematográfico, no una carrera

  let touring = false;
  let frameId = null;
  let startTime = null;
  let startY = 0;

  function maxScrollY() {
    return document.documentElement.scrollHeight - window.innerHeight;
  }

  function stopTour() {
    if (!touring) return;
    touring = false;
    if (frameId) cancelAnimationFrame(frameId);
    document.documentElement.style.scrollBehavior = '';
    btn.textContent = START_LABEL;
    btn.classList.remove('is-touring');
    window.removeEventListener('wheel', stopTour);
    window.removeEventListener('touchmove', stopTour);
    window.removeEventListener('keydown', onKeyDown);
  }

  // Cualquier tecla de navegación por teclado cuenta como "el usuario ha
  // tomado el control", igual que mover la rueda o arrastrar en móvil.
  const NAV_KEYS = ['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '];
  function onKeyDown(event) {
    if (NAV_KEYS.includes(event.key)) stopTour();
  }

  function tick(now) {
    if (!touring) return;
    const elapsedSeconds = (now - startTime) / 1000;
    const targetY = startY + elapsedSeconds * SPEED_PX_PER_SEC;
    const max = maxScrollY();

    if (targetY >= max) {
      window.scrollTo(0, max);
      stopTour();
      return;
    }

    window.scrollTo(0, targetY);
    frameId = requestAnimationFrame(tick);
  }

  function startTour() {
    touring = true;
    // `html{scroll-behavior:smooth}` (global) pelearía con fijar la
    // posición nosotros mismos en cada frame; se desactiva mientras dura
    // el tour y se restaura al terminar/cancelar.
    document.documentElement.style.scrollBehavior = 'auto';
    startY = window.scrollY;
    startTime = performance.now();
    btn.textContent = STOP_LABEL;
    btn.classList.add('is-touring');
    window.addEventListener('wheel', stopTour, { passive: true });
    window.addEventListener('touchmove', stopTour, { passive: true });
    window.addEventListener('keydown', onKeyDown);
    frameId = requestAnimationFrame(tick);
  }

  btn.addEventListener('click', () => {
    if (touring) stopTour();
    else startTour();
  });
})();
