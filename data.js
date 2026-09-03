// Contenido del sitio — edita aquí los textos, no en el HTML.
// render.js lee este fichero y genera el DOM de las secciones dinámicas.

const SITE = {
  name: 'Ludogic',
  tagline: 'Lleva tu web al siguiente nivel',
  heroKicker: 'Bienvenido a bordo',
  heroText:
    'Ludogic diseña y desarrolla webs, campus virtuales y tiendas online con el mismo rigor con el que construimos videojuegos.',
  heroCtaPrimary: { label: 'Entrar', href: '#plantas' },
  heroCtaSecondary: { label: 'Ver servicios', href: '#plantas' },
};

const NAV_LINKS = [
  { label: 'Inicio', href: '#inicio' },
  { label: 'Servicios', href: '#plantas' },
  { label: 'Portfolio', href: '#portfolio', hidden: true },
  { label: 'Contacto', href: '#contacto' },
];

// Cabeceras (kicker + título + intro) de cada sección — su propia "cajita"
// de contenido, independiente de los items que llevan dentro.
const SECTIONS = {
  floors: {
    kicker: 'Plano del edificio',
    title: 'Servicios',
    intro: 'Cinco plantas, en el orden en que más impacto tienen en tu negocio. Empezamos siempre por la base: tu web.',
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
    flag: 'Planta insignia',
    title: 'Rediseño y modernización web',
    description: 'Renovamos tu web actual: rendimiento, diseño y experiencia de usuario al día.',
    icon: 'compass',
  },
  {
    code: '02',
    flag: null,
    title: 'Campus virtuales',
    description: 'Plataformas de formación online a medida, para equipos y academias.',
    icon: 'anchor',
  },
  {
    code: '03',
    flag: null,
    title: 'Diseño y gestión de e-commerce',
    description: 'Tiendas online que venden: catálogo, pagos y gestión sin fricción.',
    icon: 'wheel',
  },
  {
    code: '04',
    flag: null,
    title: 'Videojuegos web',
    description: 'Juegos jugables desde el navegador, sin descargas ni instalaciones.',
    icon: 'porthole',
  },
  {
    code: '05',
    flag: null,
    title: 'Diseño digital',
    description: 'Identidad visual, UI y piezas gráficas para que tu marca se vea tan cuidada como funciona.',
    icon: 'wave',
  },
];

const PORTFOLIO = [
  {
    title: 'Bombs & Goblins',
    status: 'Próximamente',
    description:
      'Haz explotar a tus amigos en un sencillo juego de cartas del género filler. La prueba de que sabemos construir mecánicas de juego además de webs.',
    tags: ['Juego de cartas', 'Filler', 'Multijugador local'],
    image: 'images/BombsAndGoblins-web.jpg',
    imageAlt: 'Arte de Bombs & Goblins',
  },
];

const CONTACT = {
  kicker: 'Destino final',
  title: 'Hablemos de tu proyecto',
  text: '¿Tienes una idea, quieres colaborar o simplemente saludar? Escríbenos.',
  email: 'ludogicgames@gmail.com',
};

const FOOTER = {
  text: `© ${new Date().getFullYear()} Ludogic — Lleva tu web al siguiente nivel`,
};
