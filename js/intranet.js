const TOKEN_KEY = 'lbc-token';

function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch (e) { return null; }
}
function setToken(token) {
  try { localStorage.setItem(TOKEN_KEY, token); } catch (e) {}
}
function clearToken() {
  try { localStorage.removeItem(TOKEN_KEY); } catch (e) {}
}

async function apiFetch(url, options = {}) {
  const token = getToken();
  const headers = Object.assign({}, options.headers, {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  });
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    showLogin();
    throw new Error('unauthorized');
  }
  return res;
}

function formatDate(iso) {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}
function formatCOP(amount) {
  return '$' + Number(amount || 0).toLocaleString('es-CO');
}
function linkNode(href, text) {
  const a = document.createElement('a');
  a.href = href; a.target = '_blank'; a.rel = 'noopener';
  a.textContent = text;
  return a;
}
function colorDot(color) {
  const span = document.createElement('span');
  span.className = 'color-dot';
  span.style.background = color || '#101012';
  return span;
}
function button(label, cls, onClick) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = cls;
  btn.textContent = label;
  btn.addEventListener('click', onClick);
  return btn;
}

/* ---------- login / shell ---------- */
const loginView = document.getElementById('loginView');
const appShell = document.getElementById('appShell');
const loginForm = document.getElementById('loginForm');
const loginStatus = document.getElementById('loginStatus');
const logoutBtn = document.getElementById('logoutBtn');
const nav = document.getElementById('intranetNav');

function showLogin() {
  loginView.hidden = false;
  appShell.hidden = true;
}
function showApp() {
  loginView.hidden = true;
  appShell.hidden = false;
}

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(loginForm).entries());
  loginStatus.textContent = '';
  loginStatus.removeAttribute('data-state');
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json().catch(() => ({}));
    if (res.ok) {
      setToken(result.token);
      loginForm.reset();
      showApp();
      switchView(location.hash.replace('#', '') || 'dashboard');
    } else {
      loginStatus.textContent = result.error || 'No se pudo entrar.';
      loginStatus.setAttribute('data-state', 'error');
    }
  } catch (err) {
    loginStatus.textContent = 'No hay conexión con el servidor.';
    loginStatus.setAttribute('data-state', 'error');
  }
});

logoutBtn.addEventListener('click', () => {
  clearToken();
  showLogin();
});

/* ---------- router ---------- */
const LOADERS = {
  dashboard: loadDashboard,
  citas: loadCitas,
  personal: () => loadGeneric('personal'),
  clientes: () => loadGeneric('clientes'),
  catalogo: () => loadGeneric('catalogo'),
  inventario: () => loadGeneric('inventario'),
  gastos: () => loadGeneric('gastos'),
  marketing: () => loadGeneric('marketing'),
  descuentos: () => loadGeneric('descuentos'),
};

function switchView(view) {
  if (!LOADERS[view]) view = 'dashboard';
  document.querySelectorAll('.intranet-view').forEach(v => {
    v.hidden = v.dataset.view !== view;
  });
  nav.querySelectorAll('a').forEach(a => {
    a.classList.toggle('active', a.dataset.view === view);
  });
  location.hash = view;
  LOADERS[view]();
}

nav.addEventListener('click', (e) => {
  const link = e.target.closest('a[data-view]');
  if (!link) return;
  e.preventDefault();
  switchView(link.dataset.view);
});

window.addEventListener('hashchange', () => {
  if (!appShell.hidden) switchView(location.hash.replace('#', ''));
});

/* ---------- dashboard ---------- */
async function loadDashboard() {
  try {
    const res = await apiFetch('/api/dashboard');
    const data = await res.json();
    document.getElementById('statToday').textContent = data.today_count;
    document.getElementById('statWeek').textContent = data.week_count;
    document.getElementById('statClients').textContent = data.clients_count;
    document.getElementById('statRevenue').textContent = formatCOP(data.month_revenue);
    document.getElementById('statExpenses').textContent = formatCOP(data.month_expenses);
    document.getElementById('statLowStock').textContent = data.low_stock;

    const body = document.getElementById('dashboardNextBody');
    const empty = document.getElementById('dashboardEmpty');
    body.innerHTML = '';
    empty.hidden = data.next_appointments.length > 0;
    data.next_appointments.forEach(a => {
      const tr = document.createElement('tr');
      [formatDate(a.date), a.time, a.name, a.service].forEach(text => {
        const td = document.createElement('td');
        td.textContent = text;
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
  } catch (e) { /* apiFetch ya maneja 401 */ }
}

/* ---------- citas (a medida: estado inline + selección de profesional) ---------- */
const CITA_STATUSES = ['pendiente', 'confirmada', 'completada', 'cancelada'];

async function loadCitas() {
  try {
    const res = await apiFetch('/api/appointments');
    const data = await res.json();
    const body = document.getElementById('citasBody');
    const empty = document.getElementById('citasEmpty');
    const summary = document.getElementById('citasSummary');
    body.innerHTML = '';
    empty.hidden = data.appointments.length > 0;
    summary.textContent = data.appointments.length === 0
      ? 'No tienes citas agendadas.'
      : `${data.appointments.length} cita${data.appointments.length === 1 ? '' : 's'} en total.`;

    data.appointments.forEach(appt => {
      const tr = document.createElement('tr');

      [formatDate(appt.date), appt.time, appt.name].forEach(text => {
        const td = document.createElement('td');
        td.textContent = text;
        tr.appendChild(td);
      });

      const phoneTd = document.createElement('td');
      phoneTd.appendChild(linkNode(`https://wa.me/57${appt.phone.replace(/\D/g, '')}`, appt.phone));
      tr.appendChild(phoneTd);

      const serviceTd = document.createElement('td');
      serviceTd.textContent = appt.service;
      tr.appendChild(serviceTd);

      const barberTd = document.createElement('td');
      if (appt.staff_name) barberTd.appendChild(colorDot(appt.staff_color));
      barberTd.append(appt.staff_name || appt.barber || '—');
      tr.appendChild(barberTd);

      const statusTd = document.createElement('td');
      const select = document.createElement('select');
      select.className = 'status-select';
      CITA_STATUSES.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s; opt.textContent = s;
        if (s === appt.status) opt.selected = true;
        select.appendChild(opt);
      });
      select.addEventListener('change', async () => {
        await apiFetch(`/api/appointments/${appt.id}`, {
          method: 'PATCH', body: JSON.stringify({ status: select.value }),
        });
      });
      statusTd.appendChild(select);
      tr.appendChild(statusTd);

      const actionsTd = document.createElement('td');
      actionsTd.className = 'row-actions';
      actionsTd.appendChild(button('Eliminar', 'intranet-delete', async () => {
        if (!confirm('¿Eliminar esta cita?')) return;
        await apiFetch(`/api/appointments/${appt.id}`, { method: 'DELETE' });
        loadCitas();
      }));
      tr.appendChild(actionsTd);

      body.appendChild(tr);
    });
  } catch (e) { /* apiFetch ya maneja 401 */ }
}

document.querySelector('[data-refresh="citas"]').addEventListener('click', loadCitas);

document.querySelector('[data-add="citas"]').addEventListener('click', async () => {
  const [servicesRes, staffRes] = await Promise.all([
    apiFetch('/api/services'), apiFetch('/api/staff'),
  ]);
  const services = (await servicesRes.json()).services.filter(s => s.active);
  const staffList = (await staffRes.json()).staff.filter(s => s.active);

  modalTitle.textContent = 'Agregar cita';
  modalFields.innerHTML = '';

  const nameInput = buildField(modalFields, { name: 'name', label: 'Nombre', type: 'text', required: true });
  const phoneInput = buildField(modalFields, { name: 'phone', label: 'Teléfono', type: 'tel', required: true });
  const serviceInput = buildField(modalFields, {
    name: 'service', label: 'Servicio', type: 'select', required: true,
    options: services.map(s => s.name),
  });
  const dateInput = buildField(modalFields, { name: 'date', label: 'Fecha', type: 'date', required: true });
  const timeInput = buildField(modalFields, { name: 'time', label: 'Hora', type: 'time', required: true });
  const staffInput = buildField(modalFields, {
    name: 'staff_id', label: 'Profesional (opcional)', type: 'select',
    options: ['', ...staffList.map(s => s.id)],
    optionLabels: { '': 'Cualquiera' , ...Object.fromEntries(staffList.map(s => [s.id, s.name])) },
  });
  const notesInput = buildField(modalFields, { name: 'notes', label: 'Notas (opcional)', type: 'textarea' });

  openModalBox();
  modalForm.onsubmit = async (e) => {
    e.preventDefault();
    modalStatus.textContent = '';
    const body = {
      name: nameInput.value, phone: phoneInput.value, service: serviceInput.value,
      date: dateInput.value, time: timeInput.value, notes: notesInput.value,
      staff_id: staffInput.value || null,
    };
    const res = await fetch('/api/appointments', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    const result = await res.json().catch(() => ({}));
    if (res.ok) {
      closeModalBox();
      loadCitas();
    } else {
      modalStatus.textContent = result.error || 'No se pudo agendar.';
      modalStatus.setAttribute('data-state', 'error');
    }
  };
});

/* ---------- módulos genéricos (CRUD por tabla + modal) ---------- */
const MODULES = {
  personal: {
    listUrl: '/api/staff', createUrl: '/api/staff',
    updateUrl: id => `/api/staff/${id}`, deleteUrl: id => `/api/staff/${id}`,
    listKey: 'staff', bodyId: 'personalBody', emptyId: 'personalEmpty', title: 'profesional',
    fields: [
      { name: 'name', label: 'Nombre', type: 'text', required: true },
      { name: 'phone', label: 'Teléfono', type: 'tel' },
      { name: 'email', label: 'Correo', type: 'email' },
      { name: 'role_title', label: 'Rol', type: 'text' },
      { name: 'color', label: 'Color en la agenda', type: 'color', default: '#101012' },
      { name: 'calendar_id', label: 'ID de Google Calendar (opcional)', type: 'text' },
      { name: 'active', label: 'Activo', type: 'checkbox', default: true },
    ],
    columns: [
      { key: 'color', label: '', render: r => colorDot(r.color) },
      { key: 'name', label: 'Nombre' },
      { key: 'phone', label: 'Teléfono' },
      { key: 'email', label: 'Correo' },
      { key: 'role_title', label: 'Rol' },
      { key: 'active', label: 'Activo', render: r => (r.active ? 'Sí' : 'No') },
    ],
  },
  clientes: {
    listUrl: '/api/clients', createUrl: '/api/clients',
    updateUrl: id => `/api/clients/${id}`, deleteUrl: id => `/api/clients/${id}`,
    listKey: 'clients', bodyId: 'clientesBody', emptyId: 'clientesEmpty', title: 'cliente',
    fields: [
      { name: 'name', label: 'Nombre', type: 'text', required: true },
      { name: 'phone', label: 'Teléfono', type: 'tel', required: true, disabledOnEdit: true },
      { name: 'email', label: 'Correo', type: 'email' },
      { name: 'notes', label: 'Notas', type: 'textarea' },
    ],
    columns: [
      { key: 'name', label: 'Nombre' },
      { key: 'phone', label: 'Teléfono', render: r => linkNode(`https://wa.me/57${r.phone.replace(/\D/g, '')}`, r.phone) },
      { key: 'email', label: 'Correo', render: r => r.email || '—' },
      { key: 'visits', label: 'Visitas' },
      { key: 'last_visit', label: 'Última visita', render: r => formatDate(r.last_visit) },
    ],
  },
  catalogo: {
    listUrl: '/api/services', createUrl: '/api/services',
    updateUrl: id => `/api/services/${id}`, deleteUrl: id => `/api/services/${id}`,
    listKey: 'services', bodyId: 'catalogoBody', emptyId: 'catalogoEmpty', title: 'servicio',
    fields: [
      { name: 'name', label: 'Nombre', type: 'text', required: true },
      { name: 'description', label: 'Descripción', type: 'textarea' },
      { name: 'price', label: 'Precio (COP)', type: 'number', default: 0 },
      { name: 'duration_minutes', label: 'Duración (minutos)', type: 'number', default: 45 },
      { name: 'active', label: 'Activo', type: 'checkbox', default: true },
    ],
    columns: [
      { key: 'name', label: 'Servicio' },
      { key: 'description', label: 'Descripción' },
      { key: 'price', label: 'Precio', render: r => formatCOP(r.price) },
      { key: 'duration_minutes', label: 'Duración', render: r => `${r.duration_minutes} min` },
      { key: 'active', label: 'Activo', render: r => (r.active ? 'Sí' : 'No') },
    ],
  },
  inventario: {
    listUrl: '/api/inventory', createUrl: '/api/inventory',
    updateUrl: id => `/api/inventory/${id}`, deleteUrl: id => `/api/inventory/${id}`,
    listKey: 'inventory', bodyId: 'inventarioBody', emptyId: 'inventarioEmpty', title: 'producto',
    fields: [
      { name: 'name', label: 'Nombre', type: 'text', required: true },
      { name: 'quantity', label: 'Cantidad', type: 'number', default: 0, step: 'any' },
      { name: 'unit', label: 'Unidad', type: 'text', default: 'unidad' },
      { name: 'min_stock', label: 'Stock mínimo', type: 'number', default: 0, step: 'any' },
    ],
    columns: [
      { key: 'name', label: 'Producto' },
      { key: 'quantity', label: 'Cantidad', render: r => `${r.quantity}${Number(r.quantity) <= Number(r.min_stock) ? ' ⚠' : ''}` },
      { key: 'unit', label: 'Unidad' },
      { key: 'min_stock', label: 'Mínimo' },
    ],
  },
  gastos: {
    listUrl: '/api/expenses', createUrl: '/api/expenses',
    deleteUrl: id => `/api/expenses/${id}`, noEdit: true,
    listKey: 'expenses', bodyId: 'gastosBody', emptyId: 'gastosEmpty', title: 'gasto',
    fields: [
      { name: 'description', label: 'Descripción', type: 'text', required: true },
      { name: 'amount', label: 'Monto (COP)', type: 'number', required: true },
      { name: 'category', label: 'Categoría', type: 'text', default: 'general' },
      { name: 'expense_date', label: 'Fecha', type: 'date', required: true },
    ],
    columns: [
      { key: 'expense_date', label: 'Fecha', render: r => formatDate(r.expense_date) },
      { key: 'description', label: 'Descripción' },
      { key: 'category', label: 'Categoría' },
      { key: 'amount', label: 'Monto', render: r => formatCOP(r.amount) },
    ],
  },
  marketing: {
    listUrl: '/api/campaigns', createUrl: '/api/campaigns',
    deleteUrl: id => `/api/campaigns/${id}`, noEdit: true,
    listKey: 'campaigns', bodyId: 'marketingBody', emptyId: 'marketingEmpty', title: 'campaña',
    statusOptions: ['borrador', 'programada', 'enviada'],
    fields: [
      { name: 'name', label: 'Nombre', type: 'text', required: true },
      { name: 'message', label: 'Mensaje', type: 'textarea', required: true },
      { name: 'channel', label: 'Canal', type: 'select', options: ['whatsapp', 'email', 'instagram', 'facebook'], default: 'whatsapp' },
      { name: 'starts_at', label: 'Empieza (opcional)', type: 'date' },
      { name: 'ends_at', label: 'Termina (opcional)', type: 'date' },
    ],
    columns: [
      { key: 'name', label: 'Campaña' },
      { key: 'message', label: 'Mensaje' },
      { key: 'channel', label: 'Canal' },
      {
        key: 'status', label: 'Estado', render: (r, mod) => {
          const select = document.createElement('select');
          select.className = 'status-select';
          mod.statusOptions.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s; opt.textContent = s;
            if (s === r.status) opt.selected = true;
            select.appendChild(opt);
          });
          select.addEventListener('change', async () => {
            await apiFetch(`/api/campaigns/${r.id}`, { method: 'PATCH', body: JSON.stringify({ status: select.value }) });
          });
          return select;
        },
      },
    ],
  },
  descuentos: {
    listUrl: '/api/discount-codes', createUrl: '/api/discount-codes',
    deleteUrl: id => `/api/discount-codes/${id}`, noEdit: true,
    listKey: 'discount_codes', bodyId: 'descuentosBody', emptyId: 'descuentosEmpty', title: 'código',
    fields: [
      { name: 'code', label: 'Código', type: 'text', required: true },
      { name: 'percent_off', label: '% de descuento (opcional)', type: 'number' },
      { name: 'amount_off', label: 'Monto de descuento (opcional, COP)', type: 'number' },
      { name: 'expires_at', label: 'Vence (opcional)', type: 'date' },
      { name: 'max_uses', label: 'Usos máximos (opcional)', type: 'number' },
    ],
    columns: [
      { key: 'code', label: 'Código' },
      { key: 'discount', label: 'Descuento', render: r => (r.percent_off ? `${r.percent_off}%` : (r.amount_off ? formatCOP(r.amount_off) : '—')) },
      { key: 'expires_at', label: 'Vence', render: r => formatDate(r.expires_at) },
      { key: 'used_count', label: 'Usos', render: r => `${r.used_count}${r.max_uses ? '/' + r.max_uses : ''}` },
      {
        key: 'active', label: 'Activo', render: (r) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'intranet-edit';
          btn.textContent = r.active ? 'Sí — desactivar' : 'No — activar';
          btn.addEventListener('click', async () => {
            await apiFetch(`/api/discount-codes/${r.id}`, { method: 'PATCH', body: JSON.stringify({ active: !r.active }) });
            loadGeneric('descuentos');
          });
          return btn;
        },
      },
    ],
  },
};

async function loadGeneric(key) {
  const mod = MODULES[key];
  try {
    const res = await apiFetch(mod.listUrl);
    const data = await res.json();
    renderGenericTable(key, data[mod.listKey]);
  } catch (e) { /* apiFetch ya maneja 401 */ }
}

function renderGenericTable(key, rows) {
  const mod = MODULES[key];
  const body = document.getElementById(mod.bodyId);
  const empty = document.getElementById(mod.emptyId);
  body.innerHTML = '';
  empty.hidden = rows.length > 0;

  rows.forEach(row => {
    const tr = document.createElement('tr');
    mod.columns.forEach(col => {
      const td = document.createElement('td');
      const value = col.render ? col.render(row, mod) : (row[col.key] ?? '—');
      if (value instanceof Node) td.appendChild(value);
      else td.textContent = value;
      tr.appendChild(td);
    });

    const actionsTd = document.createElement('td');
    actionsTd.className = 'row-actions';
    if (!mod.noEdit) {
      actionsTd.appendChild(button('Editar', 'intranet-edit', () => openGenericModal(key, row)));
    }
    actionsTd.appendChild(button('Eliminar', 'intranet-delete', async () => {
      if (!confirm(`¿Eliminar este ${mod.title}?`)) return;
      await apiFetch(mod.deleteUrl(row.id), { method: 'DELETE' });
      loadGeneric(key);
    }));
    tr.appendChild(actionsTd);

    body.appendChild(tr);
  });
}

document.querySelectorAll('[data-add]').forEach(btn => {
  const key = btn.dataset.add;
  if (key === 'citas') return; // citas tiene su propio flujo arriba
  btn.addEventListener('click', () => openGenericModal(key, null));
});

function openGenericModal(key, existing) {
  const mod = MODULES[key];
  modalTitle.textContent = (existing ? 'Editar ' : 'Agregar ') + mod.title;
  modalFields.innerHTML = '';
  const inputs = {};
  mod.fields.forEach(f => {
    inputs[f.name] = buildField(modalFields, f, existing);
  });

  openModalBox();
  modalForm.onsubmit = async (e) => {
    e.preventDefault();
    modalStatus.textContent = '';
    const body = {};
    mod.fields.forEach(f => {
      const input = inputs[f.name];
      if (f.type === 'checkbox') body[f.name] = input.checked;
      else if (f.type === 'number') body[f.name] = input.value === '' ? null : Number(input.value);
      else body[f.name] = input.value;
    });

    const url = existing ? mod.updateUrl(existing.id) : mod.createUrl;
    const method = existing ? 'PATCH' : 'POST';
    try {
      const res = await apiFetch(url, { method, body: JSON.stringify(body) });
      const result = await res.json().catch(() => ({}));
      if (res.ok) {
        closeModalBox();
        loadGeneric(key);
      } else {
        modalStatus.textContent = result.error || 'No se pudo guardar.';
        modalStatus.setAttribute('data-state', 'error');
      }
    } catch (err) { /* apiFetch ya maneja 401 */ }
  };
}

/* ---------- modal genérico: helpers de UI ---------- */
const modal = document.getElementById('modal');
const modalTitle = document.getElementById('modalTitle');
const modalFields = document.getElementById('modalFields');
const modalForm = document.getElementById('modalForm');
const modalStatus = document.getElementById('modalStatus');
const modalClose = document.getElementById('modalClose');

function buildField(container, f, existing) {
  const label = document.createElement('label');
  label.className = 'field' + (f.type === 'checkbox' ? ' field-checkbox' : '');
  const span = document.createElement('span');
  span.textContent = f.label;

  let input;
  if (f.type === 'textarea') {
    input = document.createElement('textarea');
    input.rows = 3;
  } else if (f.type === 'select') {
    input = document.createElement('select');
    f.options.forEach(o => {
      const opt = document.createElement('option');
      opt.value = o;
      opt.textContent = (f.optionLabels && f.optionLabels[o] !== undefined) ? f.optionLabels[o] : o;
      input.appendChild(opt);
    });
  } else if (f.type === 'checkbox') {
    input = document.createElement('input');
    input.type = 'checkbox';
  } else {
    input = document.createElement('input');
    input.type = f.type;
    if (f.step) input.step = f.step;
  }
  input.name = f.name;
  if (f.required) input.required = true;

  if (f.type === 'checkbox') {
    input.checked = existing ? !!existing[f.name] : (f.default || false);
    label.appendChild(input);
    label.appendChild(span);
  } else {
    input.value = existing && existing[f.name] != null ? existing[f.name] : (f.default ?? '');
    label.appendChild(span);
    label.appendChild(input);
  }
  if (f.disabledOnEdit && existing) input.disabled = true;

  container.appendChild(label);
  return input;
}

function openModalBox() {
  modal.hidden = false;
  modalStatus.textContent = '';
  modalStatus.removeAttribute('data-state');
}
function closeModalBox() {
  modal.hidden = true;
  modalForm.onsubmit = null;
}
modalClose.addEventListener('click', closeModalBox);
modal.addEventListener('click', (e) => { if (e.target === modal) closeModalBox(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !modal.hidden) closeModalBox(); });

/* ---------- arranque ---------- */
if (getToken()) {
  showApp();
  switchView(location.hash.replace('#', '') || 'dashboard');
} else {
  showLogin();
}
