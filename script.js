// Menú móvil
const navToggle = document.getElementById('nav-toggle');
const mainNav = document.getElementById('main-nav');

if (navToggle && mainNav) {
  navToggle.addEventListener('click', () => {
    const isOpen = mainNav.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', isOpen);
  });

  mainNav.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      mainNav.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });
}

// Formulario de contacto: envío real vía Web3Forms (sin backend propio),
// con la clave de acceso puesta por render.js desde data.js.
const contactForm = document.getElementById('contact-form');

if (contactForm) {
  const submitBtn = document.getElementById('contact-submit');
  const statusEl = document.getElementById('contact-form-status');
  const formCopy = (typeof CONTACT !== 'undefined' && CONTACT.form) || {};

  contactForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submitBtn) submitBtn.disabled = true;
    if (submitBtn && formCopy.submitLabelSending) submitBtn.textContent = formCopy.submitLabelSending;
    if (statusEl) {
      statusEl.textContent = '';
      statusEl.classList.remove('is-error', 'is-success');
    }

    try {
      const response = await fetch('https://api.web3forms.com/submit', {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: new FormData(contactForm),
      });
      const result = await response.json();

      if (response.ok && result.success) {
        if (statusEl) {
          statusEl.textContent = formCopy.successMessage || '';
          statusEl.classList.add('is-success');
        }
        contactForm.reset();
      } else {
        throw new Error(result.message || 'Web3Forms request failed');
      }
    } catch (err) {
      if (statusEl) {
        statusEl.textContent = '';
        if (formCopy.errorMessage) statusEl.append(`${formCopy.errorMessage} `);
        const email = typeof CONTACT !== 'undefined' ? CONTACT.email : '';
        if (email) {
          const link = document.createElement('a');
          link.href = `mailto:${email}`;
          link.textContent = email;
          statusEl.append(link);
        }
        statusEl.classList.add('is-error');
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = formCopy.submitLabel || '';
      }
    }
  });
}

// Animación de aparición al hacer scroll
const fadeEls = document.querySelectorAll('.fade-in');

if (fadeEls.length) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  fadeEls.forEach((el) => observer.observe(el));
}
