// Botón "Hacer tour" del hero: baja la página sola para que se vea todo
// el recorrido (puerta, edificio, contacto) sin que el usuario tenga que
// hacer scroll. Va rápido por el hero (la puerta es la introducción, no
// hace falta verla entera) y pasa a velocidad normal justo al llegar al
// ascensor/edificio, que es la parte que sí merece la pena ver despacio.
// Se detiene solo si el usuario toma el control (rueda, arrastre táctil,
// teclas de navegación) o si vuelve a pulsar el botón. Respeta
// prefers-reduced-motion devolviendo el botón inútil en vez de animar nada.

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

  const SPEED_FAST_PX_PER_SEC = 480; // hero: solo un vistazo rápido
  const SPEED_NORMAL_PX_PER_SEC = 120; // desde el ascensor: velocidad cinematográfica

  let touring = false;
  let frameId = null;
  let startTime = null;
  let startY = 0;
  let elevatorY = 0; // dónde empieza el edificio/ascensor, calculado al arrancar

  function maxScrollY() {
    return document.documentElement.scrollHeight - window.innerHeight;
  }

  function getElevatorY() {
    const el = document.getElementById('building-scroll');
    if (!el) return 0;
    return el.getBoundingClientRect().top + window.scrollY;
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

  // Recorrido en dos tramos: rápido hasta `elevatorY`, normal a partir de
  // ahí. Si el tour arranca ya pasado ese punto, va todo a velocidad
  // normal desde el principio.
  function positionAt(elapsedSeconds) {
    if (startY >= elevatorY) {
      return startY + elapsedSeconds * SPEED_NORMAL_PX_PER_SEC;
    }
    const fastDistance = elevatorY - startY;
    const fastDuration = fastDistance / SPEED_FAST_PX_PER_SEC;
    if (elapsedSeconds <= fastDuration) {
      return startY + elapsedSeconds * SPEED_FAST_PX_PER_SEC;
    }
    return elevatorY + (elapsedSeconds - fastDuration) * SPEED_NORMAL_PX_PER_SEC;
  }

  function tick(now) {
    if (!touring) return;
    const elapsedSeconds = (now - startTime) / 1000;
    const targetY = positionAt(elapsedSeconds);
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
    document.documentElement.style.scrollBehavior = 'auto';
    startY = window.scrollY;
    elevatorY = getElevatorY();
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
