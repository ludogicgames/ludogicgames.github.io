// Gestión de cookies de analítica: Google Analytics y Metricool NO se cargan
// hasta que el visitante acepta en el banner. La decisión se recuerda en localStorage
// (aceptar/rechazar), para no volver a preguntar en cada visita. El banner
// en sí solo existe en las páginas principales (index.html / es/index.html);
// en el resto de páginas (legal, privacidad) este script solo respeta la
// decisión ya tomada, sin volver a preguntar.

(function () {
  var GA_ID = 'G-6NTZG4TBGY';
  var METRICOOL_HASH = '5e9f666209d396f3cd022f4068ea313e';
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

    var metricoolScript = document.createElement('script');
    metricoolScript.type = 'text/javascript';
    metricoolScript.src = 'https://tracker.metricool.com/resources/be.js';
    function initMetricool() {
      window.beTracker.t({ hash: METRICOOL_HASH });
    }
    metricoolScript.onreadystatechange = initMetricool;
    metricoolScript.onload = initMetricool;
    document.head.appendChild(metricoolScript);
  }

  var consent = null;
  try {
    consent = localStorage.getItem(STORAGE_KEY);
  } catch (e) {
    // Navegación privada / localStorage bloqueado: tratamos como "sin decidir"
    // pero no insistimos con el banner para no molestar sin poder recordarlo.
  }

  // Enlace "Preferencias de cookies" del footer (presente en todas las
  // páginas, con decisión ya tomada o no): permite retirar/cambiar el
  // consentimiento en cualquier momento sin tener que borrar los datos del
  // navegador. Se conecta ANTES de los "return" de abajo, para que funcione
  // también en una visita recurrente con decisión ya guardada. Si la página
  // actual no lleva el banner (páginas legales), lleva a la home, donde sí
  // se puede volver a decidir.
  var settingsLink = document.getElementById('cookie-settings-link');
  if (settingsLink) {
    settingsLink.addEventListener('click', function (event) {
      event.preventDefault();
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch (e) {
        // nada que limpiar si no hay localStorage disponible
      }
      if (document.getElementById('cookie-banner')) {
        window.location.reload();
      } else {
        window.location.href = settingsLink.getAttribute('data-home') || '/';
      }
    });
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
