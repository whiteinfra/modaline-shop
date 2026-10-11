/* ModaLine Shop — клієнт (Vanilla JS SPA). Працює з REST API /api/*, токен JWT зберігається в localStorage. */
const API = '/api';
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const money = (n) => Number(n).toLocaleString('uk-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const STATUS = { new: ['Нове', 'secondary'], paid: ['Оплачено', 'success'], shipped: ['Відправлено', 'info'], completed: ['Виконано', 'primary'], cancelled: ['Скасовано', 'danger'] };
const PAY = { success: ['Успішний', 'success'], pending: ['Очікує', 'warning'], failed: ['Невдалий', 'danger'] };
const METHOD = { card: 'Картка', cash: 'Готівка', transfer: 'Переказ' };
const NEXT = { new: ['cancelled'], paid: ['shipped', 'cancelled'], shipped: ['completed'], completed: [], cancelled: [] };
const badge = (map, k) => `<span class="badge text-bg-${map[k][1]}">${map[k][0]}</span>`;
const modal = new bootstrap.Modal('#modal');
const toastEl = new bootstrap.Toast('#toast', { delay: 2600 });
const state = { products: { page: 1 }, customers: { page: 1 }, orders: { page: 1 } };
let onSubmit = null;

function toast(msg) { $('#toastBody').textContent = msg; toastEl.show(); }
function token() { try { return localStorage.getItem('token'); } catch { return null; } }

async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(token() ? { Authorization: `Bearer ${token()}` } : {}) };
  const res = await fetch(API + path, { ...opts, headers, body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (res.status === 401 && path !== '/auth/login') { logout(); throw new Error('Сесія завершилась — увійдіть знову'); }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(Array.isArray(d) ? d.map((e) => `${e.loc.slice(-1)[0]}: ${e.msg}`).join('; ') : d || `Помилка ${res.status}`);
  }
  return data;
}
const qs = (o) => new URLSearchParams(Object.entries(o).filter(([, v]) => v !== '' && v != null && v !== false)).toString();

function pager(el, page, total, limit, go) {
  const pages = Math.max(1, Math.ceil(total / limit));
  el.innerHTML = Array.from({ length: pages }, (_, i) => `<li class="page-item ${i + 1 === page ? 'active' : ''}"><a class="page-link" href="#" data-p="${i + 1}">${i + 1}</a></li>`).join('');
  el.querySelectorAll('a').forEach((a) => a.onclick = (e) => { e.preventDefault(); go(+a.dataset.p); });
}

function openModal(title, html, submit, okText = 'Зберегти') {
  $('#mTitle').textContent = title; $('#mBody').innerHTML = html; $('#mErr').textContent = ''; $('#mOk').textContent = okText;
  onSubmit = submit; modal.show();
}
$('#mForm').onsubmit = async (e) => {
  e.preventDefault();
  try { await onSubmit(new FormData($('#mForm'))); modal.hide(); } catch (err) { $('#mErr').textContent = err.message; }
};

/* ---------- автентифікація ---------- */
$('#loginForm').onsubmit = async (e) => {
  e.preventDefault();
  try {
    const r = await api('/auth/login', { method: 'POST', body: { email: $('#lEmail').value, password: $('#lPass').value } });
    try { localStorage.setItem('token', r.access_token); localStorage.setItem('user', r.user.full_name); } catch {}
    $('#loginErr').classList.add('d-none'); location.hash = '#dashboard'; route();
  } catch (err) { $('#loginErr').textContent = err.message; $('#loginErr').classList.remove('d-none'); }
};
function logout() { try { localStorage.removeItem('token'); } catch {} location.hash = '#login'; route(); }
$('#logout').onclick = logout;

/* ---------- дашборд ---------- */
async function loadDashboard() {
  const s = await api('/stats');
  const card = (t, v, cls = '') => `<div class="col-md-3 col-lg"><div class="card stat ${cls}"><div class="card-body"><div class="text-muted small">${t}</div><div class="fs-3 fw-bold">${v}</div></div></div></div>`;
  $('#statCards').innerHTML = card('Товарів', s.products) + card('Клієнтів', s.customers) + card('Замовлень', s.orders) +
    card('Виручка, ₴', money(s.revenue), 'border-success') + card('Закінчуються (≤ 2 шт.)', s.low_stock, s.low_stock ? 'border-warning' : '');
  $('#statStatus').innerHTML = Object.keys(STATUS).map((k) => `<span class="me-3">${badge(STATUS, k)} <b>${s.orders_by_status[k] || 0}</b></span>`).join('');
  const [os, ps] = await Promise.all([api('/orders?limit=5'), api('/products?sort=stock&limit=5')]);
  $('#dashOrders').innerHTML = os.items.map((o) => `<tr><td>#${o.id}</td><td>${esc(o.customer_name)}</td><td class="text-end">${money(o.total)}</td><td>${badge(STATUS, o.status)}</td></tr>`).join('');
  $('#dashStock').innerHTML = ps.items.map((p) => `<tr><td><code>${esc(p.sku)}</code></td><td>${esc(p.name)} (${p.size})</td><td class="text-end ${p.stock === 0 ? 'text-danger fw-bold' : 'text-warning fw-bold'}">${p.stock}</td></tr>`).join('');
}

/* ---------- товари ---------- */
async function loadProducts() {
  const f = Object.fromEntries(new FormData($('#pFilters')));
  f.in_stock = $('#pInStock').checked ? 'true' : '';
  const r = await api(`/products?${qs({ ...f, page: state.products.page, limit: 8 })}`);
  $('#pCount').textContent = `· знайдено ${r.total}`;
  $('#pRows').innerHTML = r.items.map((p) => `<tr><td><code>${esc(p.sku)}</code></td><td>${esc(p.name)}</td><td>${esc(p.category)}</td><td>${p.size}</td><td>${esc(p.color)}</td>
    <td class="text-end">${money(p.price)}</td><td class="text-end ${p.stock === 0 ? 'text-danger fw-bold' : p.stock <= 2 ? 'text-warning fw-bold' : ''}">${p.stock}</td>
    <td class="text-end text-nowrap"><button class="btn btn-sm btn-outline-primary" data-edit="${p.id}">Редагувати</button> <button class="btn btn-sm btn-outline-danger" data-del="${p.id}">Видалити</button></td></tr>`).join('')
    || '<tr><td colspan="8" class="text-center text-muted py-4">Нічого не знайдено</td></tr>';
  pager($('#pPager'), r.page, r.total, r.limit, (p) => { state.products.page = p; loadProducts(); });
  $('#pRows').querySelectorAll('[data-edit]').forEach((b) => b.onclick = () => productForm(r.items.find((x) => x.id == b.dataset.edit)));
  $('#pRows').querySelectorAll('[data-del]').forEach((b) => b.onclick = async () => {
    if (!confirm('Видалити товар?')) return;
    try { await api(`/products/${b.dataset.del}`, { method: 'DELETE' }); toast('Товар видалено'); loadProducts(); } catch (e) { toast(e.message); }
  });
}
async function loadCategories() {
  const cats = await api('/products/categories');
  $('#pFilters [name=category]').innerHTML = '<option value="">Усі категорії</option>' + cats.map((c) => `<option>${esc(c)}</option>`).join('');
}
function productForm(p = {}) {
  const f = (n, l, t = 'text', extra = '') => `<div class="col-md-6 mb-2"><label class="form-label">${l}</label><input class="form-control" name="${n}" type="${t}" value="${esc(p[n] ?? '')}" ${extra}></div>`;
  const sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL'].map((s) => `<option ${p.size === s ? 'selected' : ''}>${s}</option>`).join('');
  openModal(p.id ? `Редагування товару #${p.id}` : 'Новий товар', `<div class="row">${f('sku', 'Артикул (SKU) *', 'text', 'required')}${f('name', 'Назва *', 'text', 'required')}
    ${f('category', 'Категорія *', 'text', 'required list="catList"')}<datalist id="catList">${[...$('#pFilters [name=category]').options].slice(1).map((o) => `<option>${o.value}`).join('')}</datalist>
    <div class="col-md-6 mb-2"><label class="form-label">Розмір *</label><select class="form-select" name="size">${sizes}</select></div>
    ${f('color', 'Колір *', 'text', 'required')}${f('price', 'Ціна, ₴ *', 'number', 'step="0.01" min="0.01" required')}${f('stock', 'Залишок, шт. *', 'number', 'min="0" required')}
    <div class="col-12"><label class="form-label">Опис</label><textarea class="form-control" name="description" rows="2">${esc(p.description ?? '')}</textarea></div></div>`,
    async (fd) => {
      const body = Object.fromEntries(fd); body.price = +body.price; body.stock = +body.stock;
      await api(p.id ? `/products/${p.id}` : '/products', { method: p.id ? 'PUT' : 'POST', body });
      toast(p.id ? 'Товар оновлено ✓' : 'Товар створено ✓'); loadCategories(); loadProducts();
    });
}
$('#pAdd').onclick = () => productForm();
$('#pFilters').oninput = () => { state.products.page = 1; loadProducts(); };

/* ---------- клієнти ---------- */
async function loadCustomers() {
  const r = await api(`/customers?${qs({ search: $('#cSearch').value, page: state.customers.page, limit: 8 })}`);
  $('#cCount').textContent = `· ${r.total}`;
  $('#cRows').innerHTML = r.items.map((c) => `<tr><td>${esc(c.full_name)}</td><td>${esc(c.email)}</td><td>${esc(c.phone)}</td><td>${esc(c.city)}</td><td class="text-end">${c.orders_count}</td>
    <td class="text-end text-nowrap"><button class="btn btn-sm btn-outline-primary" data-edit="${c.id}">Редагувати</button> <button class="btn btn-sm btn-outline-danger" data-del="${c.id}">Видалити</button></td></tr>`).join('')
    || '<tr><td colspan="6" class="text-center text-muted py-4">Нічого не знайдено</td></tr>';
  pager($('#cPager'), r.page, r.total, r.limit, (p) => { state.customers.page = p; loadCustomers(); });
  $('#cRows').querySelectorAll('[data-edit]').forEach((b) => b.onclick = () => customerForm(r.items.find((x) => x.id == b.dataset.edit)));
  $('#cRows').querySelectorAll('[data-del]').forEach((b) => b.onclick = async () => {
    if (!confirm('Видалити клієнта?')) return;
    try { await api(`/customers/${b.dataset.del}`, { method: 'DELETE' }); toast('Клієнта видалено'); loadCustomers(); } catch (e) { toast(e.message); }
  });
}
function customerForm(c = {}) {
  const f = (n, l, t = 'text', extra = '') => `<div class="col-md-6 mb-2"><label class="form-label">${l}</label><input class="form-control" name="${n}" type="${t}" value="${esc(c[n] ?? '')}" ${extra}></div>`;
  openModal(c.id ? `Редагування клієнта #${c.id}` : 'Новий клієнт', `<div class="row">${f('full_name', 'Ім’я та прізвище *', 'text', 'required')}${f('email', 'Email *', 'email', 'required')}
    ${f('phone', 'Телефон', 'text', 'placeholder="+380XXXXXXXXX"')}${f('city', 'Місто')}</div>`,
    async (fd) => {
      const body = Object.fromEntries([...fd].filter(([, v]) => v !== ''));
      await api(c.id ? `/customers/${c.id}` : '/customers', { method: c.id ? 'PUT' : 'POST', body });
      toast(c.id ? 'Дані клієнта оновлено ✓' : 'Клієнта створено ✓'); loadCustomers();
    });
}
$('#cAdd').onclick = () => customerForm();
$('#cSearch').oninput = () => { state.customers.page = 1; loadCustomers(); };

/* ---------- замовлення ---------- */
async function loadOrders() {
  const r = await api(`/orders?${qs({ status: $('#oStatus').value, page: state.orders.page, limit: 8 })}`);
  $('#oCount').textContent = `· ${r.total}`;
  $('#oRows').innerHTML = r.items.map((o) => `<tr><td>#${o.id}</td><td>${esc(o.customer_name)}</td><td class="small">${o.items.map((i) => `${esc(i.product_name)} ×${i.quantity}`).join(', ')}</td>
    <td class="text-end">${money(o.total)}</td><td class="text-end">${money(o.paid)}</td><td>${badge(STATUS, o.status)}</td><td class="small">${new Date(o.created_at).toLocaleString('uk-UA', { dateStyle: 'short', timeStyle: 'short' })}</td>
    <td class="text-end text-nowrap"><button class="btn btn-sm btn-outline-secondary" data-view="${o.id}">Деталі</button>
    ${NEXT[o.status].map((s) => `<button class="btn btn-sm btn-outline-${STATUS[s][1]}" data-st="${s}" data-id="${o.id}">${STATUS[s][0]}</button>`).join(' ')}</td></tr>`).join('')
    || '<tr><td colspan="8" class="text-center text-muted py-4">Замовлень немає</td></tr>';
  pager($('#oPager'), r.page, r.total, r.limit, (p) => { state.orders.page = p; loadOrders(); });
  $('#oRows').querySelectorAll('[data-view]').forEach((b) => b.onclick = () => orderDetails(r.items.find((x) => x.id == b.dataset.view)));
  $('#oRows').querySelectorAll('[data-st]').forEach((b) => b.onclick = async () => {
    try { await api(`/orders/${b.dataset.id}`, { method: 'PUT', body: { status: b.dataset.st } }); toast(`Замовлення #${b.dataset.id}: ${STATUS[b.dataset.st][0]}`); loadOrders(); } catch (e) { toast(e.message); }
  });
}
function orderDetails(o) {
  openModal(`Замовлення #${o.id} — ${o.customer_name}`, `<p>${badge(STATUS, o.status)} <span class="ms-2 text-muted">${new Date(o.created_at).toLocaleString('uk-UA')}</span></p>
    <table class="table table-sm"><thead><tr><th>Артикул</th><th>Товар</th><th class="text-end">К-сть</th><th class="text-end">Ціна</th><th class="text-end">Сума</th></tr></thead><tbody>
    ${o.items.map((i) => `<tr><td><code>${esc(i.sku)}</code></td><td>${esc(i.product_name)}</td><td class="text-end">${i.quantity}</td><td class="text-end">${money(i.unit_price)}</td><td class="text-end">${money(i.unit_price * i.quantity)}</td></tr>`).join('')}
    </tbody><tfoot><tr><th colspan="4" class="text-end">Разом:</th><th class="text-end">${money(o.total)} ₴</th></tr><tr><td colspan="4" class="text-end">Оплачено:</td><td class="text-end">${money(o.paid)} ₴</td></tr></tfoot></table>
    ${o.comment ? `<p class="mb-0"><b>Коментар:</b> ${esc(o.comment)}</p>` : ''}`, async () => {}, 'Закрити');
}
async function orderForm() {
  const [cs, ps] = await Promise.all([api('/customers?limit=100'), api('/products?in_stock=true&limit=100')]);
  const pOpt = ps.items.map((p) => `<option value="${p.id}" data-price="${p.price}">${esc(p.name)} · ${p.size} · ${esc(p.color)} — ${money(p.price)} ₴ (є ${p.stock})</option>`).join('');
  const row = () => `<div class="row g-2 mb-2 item"><div class="col-9"><select class="form-select" name="product_id">${pOpt}</select></div>
    <div class="col-2"><input class="form-control" name="quantity" type="number" min="1" value="1"></div><div class="col-1"><button type="button" class="btn btn-outline-danger w-100 rm">×</button></div></div>`;
  openModal('Нове замовлення', `<label class="form-label">Клієнт *</label><select class="form-select mb-3" name="customer_id">${cs.items.map((c) => `<option value="${c.id}">${esc(c.full_name)} — ${esc(c.email)}</option>`).join('')}</select>
    <label class="form-label">Товари *</label><div id="items">${row()}</div><button type="button" class="btn btn-sm btn-outline-secondary" id="addItem">+ позиція</button>
    <div class="mt-3"><label class="form-label">Коментар</label><input class="form-control" name="comment"></div>
    <div class="text-end fs-5 mt-3">Сума: <b id="oTotal">0,00</b> ₴</div>`,
    async () => {
      const items = [...document.querySelectorAll('#items .item')].map((r) => ({ product_id: +r.querySelector('[name=product_id]').value, quantity: +r.querySelector('[name=quantity]').value }));
      const o = await api('/orders', { method: 'POST', body: { customer_id: +$('#mBody [name=customer_id]').value, items, comment: $('#mBody [name=comment]').value || null } });
      toast(`Замовлення #${o.id} створено на ${money(o.total)} ₴ ✓`); location.hash = '#orders'; loadOrders();
    }, 'Створити замовлення');
  const recalc = () => { let t = 0; document.querySelectorAll('#items .item').forEach((r) => { const s = r.querySelector('select'); t += +s.selectedOptions[0].dataset.price * +r.querySelector('[name=quantity]').value; }); $('#oTotal').textContent = money(t); };
  const bind = () => { document.querySelectorAll('#items .rm').forEach((b) => b.onclick = () => { if (document.querySelectorAll('#items .item').length > 1) { b.closest('.item').remove(); recalc(); } }); $('#items').oninput = recalc; };
  $('#addItem').onclick = () => { $('#items').insertAdjacentHTML('beforeend', row()); bind(); recalc(); };
  bind(); recalc();
}
$('#oAdd').onclick = orderForm;
$('#oStatus').onchange = () => { state.orders.page = 1; loadOrders(); };

/* ---------- платежі ---------- */
async function loadPayments() {
  const r = await api(`/payments?${qs({ status: $('#payStatus').value, limit: 50 })}`);
  $('#payCount').textContent = `· ${r.total}`;
  $('#payRows').innerHTML = r.items.map((p) => `<tr><td>${p.id}</td><td>#${p.order_id}</td><td class="text-end">${money(p.amount)}</td><td>${METHOD[p.method]}</td><td>${badge(PAY, p.status)}</td>
    <td class="small">${p.paid_at ? new Date(p.paid_at).toLocaleString('uk-UA', { dateStyle: 'short', timeStyle: 'short' }) : '—'}</td>
    <td class="text-end">${p.status !== 'success' ? `<button class="btn btn-sm btn-outline-success" data-ok="${p.id}">Підтвердити</button>` : ''}</td></tr>`).join('');
  $('#payRows').querySelectorAll('[data-ok]').forEach((b) => b.onclick = async () => {
    try { await api(`/payments/${b.dataset.ok}`, { method: 'PUT', body: { status: 'success' } }); toast('Платіж підтверджено ✓'); loadPayments(); } catch (e) { toast(e.message); }
  });
}
async function paymentForm() {
  const os = await api('/orders?status=new&limit=100');
  if (!os.items.length) { toast('Немає неоплачених замовлень'); return; }
  openModal('Реєстрація платежу', `<label class="form-label">Замовлення *</label><select class="form-select mb-2" name="order_id">${os.items.map((o) => `<option value="${o.id}" data-rest="${o.total - o.paid}">#${o.id} — ${esc(o.customer_name)} — ${money(o.total)} ₴</option>`).join('')}</select>
    <div class="row"><div class="col-md-4"><label class="form-label">Сума, ₴ *</label><input class="form-control" name="amount" type="number" step="0.01" min="0.01" required></div>
    <div class="col-md-4"><label class="form-label">Спосіб</label><select class="form-select" name="method"><option value="card">Картка</option><option value="cash">Готівка</option><option value="transfer">Переказ</option></select></div>
    <div class="col-md-4"><label class="form-label">Статус</label><select class="form-select" name="status"><option value="success">Успішний</option><option value="pending">Очікує</option><option value="failed">Невдалий</option></select></div></div>`,
    async (fd) => {
      const b = Object.fromEntries(fd); b.order_id = +b.order_id; b.amount = +b.amount;
      await api('/payments', { method: 'POST', body: b }); toast('Платіж зареєстровано ✓'); loadPayments();
    });
  const sel = $('#mBody [name=order_id]'); const fill = () => { $('#mBody [name=amount]').value = (+sel.selectedOptions[0].dataset.rest).toFixed(2); };
  sel.onchange = fill; fill();
}
$('#payAdd').onclick = paymentForm;
$('#payStatus').onchange = loadPayments;

/* ---------- маршрутизація ---------- */
const VIEWS = { dashboard: loadDashboard, products: () => { loadCategories(); loadProducts(); }, customers: loadCustomers, orders: loadOrders, payments: loadPayments };
function route() {
  const v = location.hash.slice(1) || 'dashboard';
  const logged = !!token();
  $('#view-login').classList.toggle('d-none', logged && v !== 'login');
  $('#view-app').classList.toggle('d-none', !logged || v === 'login');
  if (!logged || v === 'login') return;
  try { $('#who').textContent = localStorage.getItem('user') || ''; } catch {}
  document.querySelectorAll('.view').forEach((s) => s.classList.toggle('d-none', s.id !== `view-${v}`));
  document.querySelectorAll('#nav a').forEach((a) => a.classList.toggle('active', a.getAttribute('href') === `#${v}`));
  (VIEWS[v] || loadDashboard)().catch((e) => toast(e.message));
}
window.addEventListener('hashchange', route);
route();
