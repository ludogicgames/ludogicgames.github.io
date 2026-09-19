// Gestión de cookies de analítica: Google Analytics NO se carga hasta que el
// visitante acepta en el banner. La decisión se recuerda en localStorage
// (aceptar/rechazar), para no volver a preguntar en cada visita. El banner
// en sí solo existe en las páginas principales (index.html / es/index.html);
// en el resto de páginas (legal, privacidad) este script solo respeta la
// decisión ya tomada, sin volver a preguntar.

(function () {
  var GA_ID = 'G-6NTZG4TBGY';
  var STORAGE_KEY = 'ludogic-cookie-consent';

  function loadAnalytics() {
    window.dataLayer = window.dataLayer || [];
    function gtag() { dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag('js', new Date());
    gtag('config', GA_ID);

    var script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(script);
  }

  var consent = null;
  try {
    consent = localStorage.getItem(STORAGE_KEY);
  } catch (e) {
    // Navegación privada / localStorage bloqueado: tratamos como "sin decidir"
    // pero no insistimos con el banner para no molestar sin poder recordarlo.
  }

  if (consent === 'accepted') {
    loadAnalytics();
    return;
  }
  if (consent === 'rejected') {
    return;
  }

  var banner = document.getElementById('cookie-banner');
  if (!banner) return; // esta página no lleva el banner (p.ej. páginas legales)

  banner.hidden = false;

  function decide(value) {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch (e) {
      // si no se puede guardar, simplemente se volverá a preguntar la próxima vez
    }
    banner.hidden = true;
    if (value === 'accepted') loadAnalytics();
  }

  var acceptBtn = document.getElementById('cookie-accept');
  var rejectBtn = document.getElementById('cookie-reject');
  if (acceptBtn) acceptBtn.addEventListener('click', function () { decide('accepted'); });
  if (rejectBtn) rejectBtn.addEventListener('click', function () { decide('rejected'); });
})();
