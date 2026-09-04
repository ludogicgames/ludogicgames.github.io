// Efecto de scroll para el panel de contacto: justo al terminar de bajar
// por el edificio, el panel entra deslizándose desde la derecha, como si
// el recorrido girase hacia el destino final. Solo transform/opacity por
// CSS (sin Three.js), así que no depende de que cargue el CDN. Mejora
// progresiva: sin JS (o con prefers-reduced-motion) el panel se ve
// igualmente, ya en su sitio, gracias a los valores por defecto del CSS.

(function () {
  const scrollWrap = document.getElementById('contact-scroll');
  const sticky = document.getElementById('contact-sticky');
  const panel = document.getElementById('contact-panel');
  if (!scrollWrap || !sticky || !panel) return;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reducedMotion) return;

  function clamp01(v) {
    return Math.max(0, Math.min(1, v));
  }

  function getScrollProgress() {
    const rect = scrollWrap.getBoundingClientRect();
    const total = rect.height - window.innerHeight;
    if (total <= 0) return 1;
    return clamp01(-rect.top / total);
  }

  function applyProgress(progress) {
    // La entrada ocupa la primera mitad del recorrido; el resto es una
    // pausa con el panel ya en su sitio, para dar tiempo a leerlo/rellenarlo
    // antes de que el scroll siga hacia el pie de página.
    const slide = clamp01(progress / 0.5);
    const eased = 1 - Math.pow(1 - slide, 3);
    panel.style.transform = `translateX(${(1 - eased) * 100}%)`;
    panel.style.opacity = String(0.25 + eased * 0.75);
  }

  let ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      applyProgress(getScrollProgress());
      ticking = false;
    });
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  applyProgress(getScrollProgress());
})();
