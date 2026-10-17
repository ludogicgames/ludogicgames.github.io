// Contenido del sitio — edita aquí los textos, no en el HTML.
// render.js lee este fichero y genera el DOM de las secciones dinámicas.
// (Versión en inglés: data.en.js — mantener los dos sincronizados al editar.)

const SITE = {
  name: 'Ludogic',
  tagline: 'Gamificación B2B',
  heroKicker: 'Expertos en gamificación',
  heroText:
    'Trabajamos por objetivos pactados con tu empresa: si no se cumplen, no cobramos. Garantizado por contrato.',
  // Botón de tour.js: baja la página sola (rápido en el hero, a la
  // velocidad normal a partir del ascensor).
  heroCtaTour: { label: 'Hacer tour', stopLabel: 'Detener tour' },
  heroScrollHint: 'Desliza para entrar ↓',
  buildingScrollHint: 'Sigue bajando ↓',
  navMenuLabel: 'Abrir menú',
};

const NAV_LINKS = [
  { label: 'Inicio', href: '#inicio' },
  { label: 'Qué hacemos', href: '#plantas' },
  { label: 'Portfolio', href: '#portfolio', hidden: true },
  { label: 'Contacto', href: '#contacto', cta: true },
];

// Cabeceras (kicker + título + intro) de cada sección — su propia "cajita"
// de contenido, independiente de los items que llevan dentro.
const SECTIONS = {
  floors: {
    kicker: 'Especialistas en gamificación',
    title: 'Qué hacemos',
    intro: 'Diseñamos y desarrollamos experiencias con mentalidad de videojuego: formación, marketing y producto que la gente sí termina, sí juega y sí vuelve.',
  },
  portfolio: {
    kicker: 'Cuaderno de bitácora',
    title: 'Portfolio',
    intro: 'Nuestro primer título propio, en desarrollo.',
  },
};

// Ponlo en `true` cuando haya portfolio real que mostrar. El contenido y la
// sección siguen existiendo (no se borra nada), solo se ocultan.
const PORTFOLIO_VISIBLE = false;

// Cada "planta" es un servicio. El orden es el orden real de prioridad de negocio:
// se muestran de arriba (planta 01, la más destacada) hacia abajo.
const FLOORS = [
  {
    code: '01',
    flag: null,
    title: 'Formación gamificada',
    description: 'Diseñamos y mejoramos plataformas de e-learning y formación corporativa con mecánicas de juego que aumentan el engagement: más eficacia, menos abandono y aprendizaje más rápido. Ideal para empresas de e-learning, escuelas, campus virtuales y equipos que quieran formar a su plantilla.',
    icon: 'compass',
  },
  {
    code: '02',
    flag: null,
    title: 'Advergaming',
    description: 'Creamos campañas gamificadas junto al equipo de marketing: minijuegos, yincanas, retos y más. Entretenimiento que hace que tu audiencia quiera consumir más contenido de la marca, además de aumentar la viralidad.',
    icon: 'wave',
  },
  {
    code: '03',
    flag: null,
    title: 'Productos y servicios gamificados',
    description: 'Gamificamos productos y servicios para que las fases de onboarding, compra y activación sean más atractivas e intuitivas, además de aumentar la retención y mejorar la UX. Ideal para empresas de SaaS, e-commerce, apps móviles, campus virtuales y retail.',
    icon: 'anchor',
  },
  {
    code: '04',
    flag: null,
    title: 'Eventos gamificados',
    description: 'Creamos dinámicas de juego para eventos, fiestas y congresos, con objetivos concretos como el teambuilding, el networking, o simplemente entretenimiento. Ideal para empresas de eventos, wedding planners o empresas que quieran organizar un evento o congreso.',
    icon: 'calendar',
  },
];

const PORTFOLIO = [
  {
    title: 'Bombs & Goblins',
    status: 'Próximamente',
    description:
      'Haz explotar a tus amigos en un sencillo juego de cartas del género filler. La prueba de que sabemos construir mecánicas de juego además de webs.',
    tags: ['Juego de cartas', 'Filler', 'Multijugador local'],
    image: '/images/BombsAndGoblins-web.jpg',
    imageAlt: 'Arte de Bombs & Goblins',
  },
];

const CONTACT = {
  kicker: 'Destino final',
  title: 'Hablemos de tu proyecto',
  text: '¿Tienes una idea, quieres colaborar o simplemente saludar? Cuéntanoslo.',
  email: 'hello@ludogic.dev',
  // Asunto del email que le llega a Ludogic (no lo ve la visita) — en el
  // idioma que sea útil para vosotros al triar, no hace falta que
  // coincida con el idioma de la página.
  emailSubject: 'Nuevo mensaje desde ludogic.dev/es',
  // El formulario envía de verdad a través de Web3Forms (sin backend
  // propio): https://web3forms.com — la clave es pública a propósito,
  // es como funciona el servicio (no da acceso a nada, solo identifica
  // a qué email reenviar). Si hay que cambiar el email de destino, se
  // genera una clave nueva en web3forms.com y se sustituye aquí.
  web3formsAccessKey: 'c433de79-c2fd-44a7-83dc-174eb2324d8b',
  form: {
    nameLabel: 'Nombre',
    namePlaceholder: 'Tu nombre',
    emailLabel: 'Correo electrónico',
    emailPlaceholder: 'tu@correo.com',
    messageLabel: 'Mensaje',
    messagePlaceholder: 'Cuéntanos en qué podemos ayudarte',
    submitLabel: 'Enviar',
    submitLabelSending: 'Enviando…',
    successMessage: 'Mensaje enviado — te responderemos lo antes posible.',
    errorMessage: 'No se ha podido enviar. Escríbenos directamente a',
    note: 'También puedes escribirnos directamente a',
    consentRequiredMessage: 'Acepta la Política de Privacidad antes de enviar.',
  },
};

const FOOTER = {
  text: `© ${new Date().getFullYear()} Ludogic — El siguiente nivel de la gamificación`,
};

// Banner que se muestra una vez (ver cookie-consent.js) antes de permitir
// que cargue Google Analytics — la decisión se recuerda en localStorage.
const COOKIE_CONSENT = {
  message: 'Usamos cookies de analítica para entender cómo se usa la web.',
  policyLinkLabel: 'Saber más',
  acceptLabel: 'Aceptar',
  rejectLabel: 'Rechazar',
};
