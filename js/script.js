// Año en footer
document.getElementById('year').textContent = new Date().getFullYear();

// Pantalla de bienvenida (una vez por sesión)
const intro = document.getElementById('intro');
let seenIntro = false;
try { seenIntro = sessionStorage.getItem('lbc-intro') === '1'; } catch (e) {}

if (seenIntro) {
  intro.remove();
} else {
  document.body.style.overflow = 'hidden';
  setTimeout(() => {
    intro.classList.add('leaving');
    document.body.style.overflow = '';
    try { sessionStorage.setItem('lbc-intro', '1'); } catch (e) {}
    intro.addEventListener('transitionend', () => intro.remove(), { once: true });
  }, 1500);
}

// Menú móvil
const burger = document.getElementById('burger');
const nav = document.getElementById('nav');
burger.addEventListener('click', () => {
  burger.classList.toggle('open');
  nav.classList.toggle('open');
});
nav.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => {
    burger.classList.remove('open');
    nav.classList.remove('open');
  });
});

// Lightbox de la galería
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightboxImg');
const lightboxClose = document.getElementById('lightboxClose');

document.querySelectorAll('.gallery-item').forEach(item => {
  item.addEventListener('click', () => {
    const full = item.getAttribute('data-full');
    const alt = item.querySelector('img').alt;
    lightboxImg.src = full;
    lightboxImg.alt = alt;
    lightbox.classList.add('open');
    document.body.style.overflow = 'hidden';
  });
});

function closeLightbox() {
  lightbox.classList.remove('open');
  document.body.style.overflow = '';
}
lightboxClose.addEventListener('click', closeLightbox);
lightbox.addEventListener('click', (e) => {
  if (e.target === lightbox) closeLightbox();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeLightbox();
});

// Formulario de reserva
const bookingForm = document.getElementById('bookingForm');
const bookingStatus = document.getElementById('bookingStatus');
const dateInput = bookingForm.querySelector('input[name="date"]');
dateInput.min = new Date().toISOString().slice(0, 10);

// Carga el catálogo de servicios y el equipo desde la API (ya no van fijos en el HTML)
const serviceSelect = document.getElementById('serviceSelect');
const FALLBACK_SERVICES = ['Barbería', 'Peluquería', 'Uñas'];

function fillServiceSelect(names) {
  serviceSelect.innerHTML = '<option value="">Elige uno</option>';
  names.forEach(name => {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    serviceSelect.appendChild(opt);
  });
}

fetch('/api/services/public')
  .then(res => res.json())
  .then(data => {
    if (!data.services || !data.services.length) throw new Error('empty');
    fillServiceSelect(data.services.map(s => s.name));
  })
  .catch(() => fillServiceSelect(FALLBACK_SERVICES));

const staffSelect = document.getElementById('staffSelect');
fetch('/api/staff/public')
  .then(res => res.json())
  .then(data => {
    data.staff.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = s.name;
      staffSelect.appendChild(opt);
    });
  })
  .catch(() => {});

// Las tarjetas de servicio llevan al formulario con el servicio ya elegido
document.querySelectorAll('.service-card[data-service]').forEach(card => {
  card.addEventListener('click', () => {
    const service = card.dataset.service;
    if (service) serviceSelect.value = service;
  });
});

// Carrusel de testimonios
const testimonialRail = document.getElementById('testimonialRail');
const testimonialPrev = document.getElementById('testimonialPrev');
const testimonialNext = document.getElementById('testimonialNext');
if (testimonialRail && testimonialPrev && testimonialNext) {
  const scrollByCard = (direction) => {
    const card = testimonialRail.querySelector('.testimonial-card');
    const amount = card ? card.getBoundingClientRect().width + 24 : 300;
    testimonialRail.scrollBy({ left: direction * amount, behavior: 'smooth' });
  };
  testimonialPrev.addEventListener('click', () => scrollByCard(-1));
  testimonialNext.addEventListener('click', () => scrollByCard(1));
}

bookingForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const submitBtn = bookingForm.querySelector('button[type="submit"]');
  const data = Object.fromEntries(new FormData(bookingForm).entries());

  bookingStatus.textContent = '';
  bookingStatus.removeAttribute('data-state');
  submitBtn.disabled = true;

  try {
    const res = await fetch('/api/appointments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const result = await res.json().catch(() => ({}));

    if (res.ok) {
      bookingStatus.textContent = `Listo, ${data.name.split(' ')[0]}. Te esperamos el ${data.date} a las ${data.time}.`;
      bookingStatus.setAttribute('data-state', 'ok');
      bookingForm.reset();
    } else {
      bookingStatus.textContent = result.error || 'No pudimos agendar la cita. Intenta de nuevo.';
      bookingStatus.setAttribute('data-state', 'error');
    }
  } catch (err) {
    bookingStatus.textContent = 'No hay conexión con el servidor. Intenta de nuevo o escríbenos por WhatsApp.';
    bookingStatus.setAttribute('data-state', 'error');
  } finally {
    submitBtn.disabled = false;
  }
});
