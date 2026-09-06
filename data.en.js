// Site content — edit the text here, not in the HTML.
// render.js reads this file and generates the DOM for the dynamic sections.
// (Spanish version: data.es.js — keep both in sync when editing copy.)

const SITE = {
  name: 'Ludogic',
  tagline: 'Take your web to the next level',
  heroKicker: 'Gamification experts',
  heroText:
    'Ludogic designs and builds experiences with a game designer’s mindset: gamification for training, marketing and product, plus custom web games.',
  // tour.js button: scrolls the page down on its own (fast through the
  // hero, then at normal speed from the elevator onward).
  heroCtaTour: { label: 'Take a tour', stopLabel: 'Stop tour' },
  heroScrollHint: 'Scroll to enter ↓',
  buildingScrollHint: 'Keep scrolling ↓',
  navMenuLabel: 'Open menu',
};

const NAV_LINKS = [
  { label: 'Home', href: '#inicio' },
  { label: 'Services', href: '#plantas' },
  { label: 'Portfolio', href: '#portfolio', hidden: true },
  { label: 'Contact', href: '#contacto' },
];

// Headers (kicker + title + intro) for each section — its own "box" of
// content, independent from the items inside it.
const SECTIONS = {
  floors: {
    kicker: 'Gamification specialists',
    title: 'Services',
    intro: 'We design and build experiences with a game designer’s mindset: training, marketing and product that people actually finish, actually play, and actually come back to.',
  },
  portfolio: {
    kicker: 'Ship’s log',
    title: 'Portfolio',
    intro: 'Our first original title, in development.',
  },
};

// Set to `true` once there's real portfolio work to show. The content and
// the section keep existing (nothing gets deleted), it just stays hidden.
const PORTFOLIO_VISIBLE = false;

// Each "floor" is a service. The order is the real business priority
// order: shown from the top (floor 01, the most prominent) downward.
const FLOORS = [
  {
    code: '01',
    flag: null,
    title: 'Training people actually finish',
    description: 'We design and build e-learning platforms with game mechanics —progress, challenges, rewards— so people actually finish their courses.',
    icon: 'compass',
  },
  {
    code: '02',
    flag: null,
    title: 'Campaigns people play',
    description: 'We design and build branded mini-games, interactive contests and advergaming experiences for campaigns people remember.',
    icon: 'wave',
  },
  {
    code: '03',
    flag: null,
    title: 'Products that hook',
    description: 'We design and build game mechanics for onboarding, activation and retention in your app or SaaS product.',
    icon: 'anchor',
  },
  {
    code: '04',
    flag: null,
    title: 'Web games',
    description: 'We design and build HTML5 games playable straight from the browser — no downloads, no installs.',
    icon: 'porthole',
  },
];

const PORTFOLIO = [
  {
    title: 'Bombs & Goblins',
    status: 'Coming soon',
    description:
      'Blow up your friends in a simple filler card game. Proof that we know how to build game mechanics, not just websites.',
    tags: ['Card game', 'Filler', 'Local multiplayer'],
    image: '/images/BombsAndGoblins-web.jpg',
    imageAlt: 'Bombs & Goblins artwork',
  },
];

const CONTACT = {
  kicker: 'Final destination',
  title: 'Let’s talk about your project',
  text: 'Got an idea, want to collaborate, or just want to say hi? Tell us.',
  email: 'ludogicgames@gmail.com',
  // Subject of the email Ludogic receives (visitors never see it) — pick
  // whatever language is useful for triage, it doesn't need to match the
  // page language.
  emailSubject: 'New message from ludogic.dev',
  // The form sends for real through Web3Forms (no backend of our own):
  // https://web3forms.com — the key is public on purpose, that's how the
  // service works (it doesn't grant access to anything, it only tells
  // Web3Forms which email to forward to). To change the destination
  // email, generate a new key at web3forms.com and swap it in here.
  web3formsAccessKey: 'c433de79-c2fd-44a7-83dc-174eb2324d8b',
  form: {
    nameLabel: 'Name',
    namePlaceholder: 'Your name',
    emailLabel: 'Email address',
    emailPlaceholder: 'you@email.com',
    messageLabel: 'Message',
    messagePlaceholder: 'Tell us how we can help',
    submitLabel: 'Send',
    submitLabelSending: 'Sending…',
    successMessage: 'Message sent — we’ll get back to you as soon as possible.',
    errorMessage: 'Couldn’t send it. Email us directly at',
    note: 'You can also email us directly at',
  },
};

const FOOTER = {
  text: `© ${new Date().getFullYear()} Ludogic — Take your web to the next level`,
};
