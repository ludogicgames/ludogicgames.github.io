// Genera el DOM de las secciones dinámicas a partir de data.js.
// Para cambiar contenido (plantas, portfolio, contacto...) edita data.js, no este fichero.

const ICONS = {
  compass:
    '<circle cx="12" cy="12" r="9"></circle><path d="M15.5 8.5l-2 5-5 2 2-5 5-2z"></path>',
  anchor:
    '<circle cx="12" cy="5" r="2"></circle><path d="M12 7v13M7 13H3a9 9 0 0 0 9 8 9 9 0 0 0 9-8h-4" stroke-linecap="round"></path><path d="M8 10h8" stroke-linecap="round"></path>',
  wheel:
    '<circle cx="12" cy="12" r="7"></circle><circle cx="12" cy="12" r="2"></circle><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" stroke-linecap="round"></path>',
  porthole:
    '<circle cx="12" cy="12" r="8"></circle><circle cx="12" cy="12" r="5"></circle><path d="M12 4v3M12 17v3M4 12h3M17 12h3" stroke-linecap="round"></path>',
  wave:
    '<path d="M3 10c2 0 2-2.5 4-2.5S9 10 11 10s2-2.5 4-2.5S17 10 19 10s2-2.5 2-2.5" stroke-linecap="round"></path><path d="M3 15c2 0 2-2.5 4-2.5S9 15 11 15s2-2.5 4-2.5S17 15 19 15s2-2.5 2-2.5" stroke-linecap="round"></path>',
};

function icon(name, extraClass) {
  const paths = ICONS[name] || '';
  return `<svg class="icon ${extraClass || ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">${paths}</svg>`;
}

function renderNav() {
  const nav = document.getElementById('nav-links');
  if (!nav) return;
  nav.innerHTML = NAV_LINKS.filter((l) => !l.hidden)
    .map((l) => `<li><a href="${l.href}">${l.label}</a></li>`)
    .join('');
}

// Cabecera (kicker + título + intro) de una sección — ver data.js:SECTIONS
function renderSectionHead(key, prefix) {
  const section = SECTIONS[key];
  if (!section) return;
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };
  setText(`${prefix}-kicker`, section.kicker);
  setText(`${prefix}-title`, section.title);
  setText(`${prefix}-intro`, section.intro);
}

function renderHero() {
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };
  setText('hero-kicker', SITE.heroKicker);
  setText('hero-title', SITE.tagline);
  setText('hero-text', SITE.heroText);

  const ctaPrimary = document.getElementById('hero-cta-primary');
  if (ctaPrimary) {
    ctaPrimary.textContent = SITE.heroCtaPrimary.label;
    ctaPrimary.href = SITE.heroCtaPrimary.href;
  }
  const ctaSecondary = document.getElementById('hero-cta-secondary');
  if (ctaSecondary) {
    ctaSecondary.textContent = SITE.heroCtaSecondary.label;
    ctaSecondary.href = SITE.heroCtaSecondary.href;
  }
}

function renderFloors() {
  renderSectionHead('floors', 'floors');

  const wrap = document.getElementById('floor-panels');
  if (!wrap) return;

  // Un panel HTML por planta, superpuesto al lienzo 3D (building3d.js);
  // building3d.js decide cuál mostrar según en qué planta esté la cámara.
  wrap.innerHTML = FLOORS.map((floor, i) => `
    <article class="floor-panel" data-floor-index="${i}" data-code="${floor.code}">
      <div class="floor-panel-inner">
        ${floor.flag ? `<span class="floor-flag">${floor.flag}</span>` : ''}
        <span class="floor-code">Planta ${floor.code}</span>
        <h3>${icon(floor.icon)}${floor.title}</h3>
        <p>${floor.description}</p>
      </div>
    </article>
  `).join('');
}

function renderPortfolio() {
  const section = document.getElementById('portfolio');
  if (section) section.hidden = !PORTFOLIO_VISIBLE;
  if (!PORTFOLIO_VISIBLE) return;

  renderSectionHead('portfolio', 'portfolio');

  const wrap = document.getElementById('portfolio-list');
  if (!wrap) return;

  wrap.innerHTML = PORTFOLIO.map((item) => `
    <div class="showcase">
      <div class="showcase-media">
        <span class="showcase-ribbon">${item.status}</span>
        <img src="${item.image}" alt="${item.imageAlt}" width="960" height="845" loading="lazy">
      </div>
      <div class="showcase-body">
        <h3>${item.title}</h3>
        <p>${item.description}</p>
        <div class="tag-row">
          ${item.tags.map((t) => `<span class="tag">${t}</span>`).join('')}
        </div>
      </div>
    </div>
  `).join('');
}

function renderContact() {
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };
  setText('contact-kicker', CONTACT.kicker);
  setText('contact-title', CONTACT.title);
  setText('contact-text', CONTACT.text);

  const form = CONTACT.form || {};
  setText('contact-name-label', form.nameLabel);
  setText('contact-email-label', form.emailLabel);
  setText('contact-message-label', form.messageLabel);
  setText('contact-submit', form.submitLabel);

  const setPlaceholder = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.placeholder = value || '';
  };
  setPlaceholder('contact-name', form.namePlaceholder);
  setPlaceholder('contact-email-field', form.emailPlaceholder);
  setPlaceholder('contact-message', form.messagePlaceholder);

  const accessKeyInput = document.getElementById('contact-access-key');
  if (accessKeyInput) accessKeyInput.value = CONTACT.web3formsAccessKey || '';

  const note = document.getElementById('contact-form-note');
  if (note) {
    note.textContent = '';
    if (form.note) note.append(`${form.note} `);
    const link = document.createElement('a');
    link.href = `mailto:${CONTACT.email}`;
    link.textContent = CONTACT.email;
    note.append(link);
  }
}

function renderFooter() {
  const el = document.getElementById('footer-text');
  if (el) el.textContent = FOOTER.text;
}

function renderLogo() {
  document.querySelectorAll('[data-site-name]').forEach((el) => {
    el.textContent = SITE.name;
  });
}

// Scripts cargados con `defer` se ejecutan tras el parseo del DOM y en orden de
// aparición, así que no hace falta esperar a DOMContentLoaded: para cuando este
// fichero corre, el HTML ya existe. Se ejecuta en línea para que script.js
// (cargado después) encuentre los enlaces del menú ya generados.
renderLogo();
renderNav();
renderHero();
renderFloors();
renderPortfolio();
renderContact();
renderFooter();
document.dispatchEvent(new CustomEvent('ludogic:rendered'));
