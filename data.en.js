// Site content — edit the text here, not in the HTML.
// render.js reads this file and generates the DOM for the dynamic sections.
// (Spanish version: data.es.js — keep both in sync when editing copy.)

const SITE = {
  name: 'Ludogic',
  tagline: 'B2B Gamification',
  heroKicker: 'Gamification experts',
  heroText:
    'We work toward goals agreed with your company: if they’re not met, we don’t charge. Guaranteed by contract.',
  // tour.js button: scrolls the page down on its own (fast through the
  // hero, then at normal speed from the elevator onward).
  heroCtaTour: { label: 'Take a tour', stopLabel: 'Stop tour' },
  heroScrollHint: 'Scroll to enter ↓',
  buildingScrollHint: 'Keep scrolling ↓',
  navMenuLabel: 'Open menu',
};

const NAV_LINKS = [
  { label: 'Home', href: '#inicio' },
  { label: 'What we do', href: '#plantas' },
  { label: 'Methodology', href: '#metodologia' },
  { label: 'Portfolio', href: '#portfolio', hidden: true },
  { label: 'Contact', href: '#contacto', cta: true },
];

// Headers (kicker + title + intro) for each section — its own "box" of
// content, independent from the items inside it.
const SECTIONS = {
  portfolio: {
    kicker: 'Ship’s log',
    title: 'Portfolio',
    intro: 'Our first original title, in development.',
  },
  methodology: {
    kicker: 'Gamification for businesses',
    title: 'Our methodology',
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
    title: 'Gamified training',
    description: 'We design and upgrade e-learning and corporate training platforms with game mechanics that boost engagement: more effective learning, lower drop-off, and faster skill-building. Ideal for e-learning companies, schools, virtual campuses, and teams who want to train their staff.',
    icon: 'compass',
  },
  {
    code: '02',
    flag: null,
    title: 'Advergaming',
    description: 'We create gamified campaigns together with the marketing team: mini-games, scavenger hunts, challenges and more. Entertainment that gets your audience wanting more branded content, while boosting virality.',
    icon: 'wave',
  },
  {
    code: '03',
    flag: null,
    title: 'Gamified products and services',
    description: 'We gamify products and services to make onboarding, purchase and activation more engaging and intuitive, while boosting retention and improving UX. Ideal for SaaS companies, e-commerce, mobile apps, virtual campuses and retail.',
    icon: 'anchor',
  },
  {
    code: '04',
    flag: null,
    title: 'Gamified events',
    description: 'We create game dynamics for events, parties and conferences, with concrete goals like team building, networking, or just pure entertainment. Ideal for event companies, wedding planners, or businesses organizing an event or conference.',
    icon: 'calendar',
  },
];

// The 5 methodology steps, in clockwise order around the circular diagram
// (see METHODOLOGY_GUARANTEE for the text at the center).
const METHODOLOGY = [
  {
    code: '01',
    title: 'NDA',
    description: 'Before we start, we sign a non-disclosure agreement to protect our client.',
  },
  {
    code: '02',
    title: 'Analysis',
    description: 'Our team analyzes the project’s needs and goals, and sets the KPIs to be measured.',
  },
  {
    code: '03',
    title: 'Budget and guarantees',
    description: 'We send a budget along with concrete, measurable goals, set out in the contract.',
  },
  {
    code: '04',
    title: 'Execution',
    description: 'We coordinate with the relevant teams at the client’s company to hit the gamified goals.',
  },
  {
    code: '05',
    title: 'Measurement and results',
    description: 'We measure the contract’s KPIs plus other parameters objectively, and deliver an analysis and recommendations report.',
  },
  {
    code: '06',
    title: 'Follow-up',
    description: 'Ludogic always cares about its clients and maintains its high quality standard by offering support after delivery.',
  },
];

const METHODOLOGY_GUARANTEE = 'Guarantee: if we don’t meet the goals, we don’t charge.';

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
  kicker: 'Contact',
  title: 'Power up your business today',
  text: 'Want to gamify training, a service, an event, or have a question for us? Tell us.',
  email: 'hello@ludogic.dev',
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
    companyLabel: 'Company name (optional)',
    companyPlaceholder: 'Your company’s name',
    emailLabel: 'Email address',
    emailPlaceholder: 'you@company.com',
    messageLabel: 'Message',
    messagePlaceholder: 'Tell us how we can help',
    submitLabel: 'Send',
    submitLabelSending: 'Sending…',
    successMessage: 'Message sent. We’ll get back to you as soon as possible.',
    errorMessage: 'Couldn’t send it. Email us directly at',
    note: 'You can also email us directly at',
    consentRequiredMessage: 'Please accept the Privacy Policy before sending.',
  },
};

const FOOTER = {
  text: `© ${new Date().getFullYear()} Ludogic — The next level of gamification`,
};

// Banner shown once (see cookie-consent.js) before Google Analytics is
// allowed to load — the choice is remembered in localStorage.
const COOKIE_CONSENT = {
  message: 'We use analytics cookies to understand how the site is used.',
  policyLinkLabel: 'Learn more',
  acceptLabel: 'Accept',
  rejectLabel: 'Reject',
};
