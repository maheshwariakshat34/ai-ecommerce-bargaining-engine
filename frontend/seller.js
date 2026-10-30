/* seller.js — Seller Dashboard logic */

const API = {
  dashboard: '/api/seller/dashboard',
  deals:     '/api/seller/deals',
  orders:    '/api/seller/orders',
};

// ── Helpers ────────────────────────────────────────────────────────────────
function inr(n) {
  return '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function timeAgo(isoString) {
  if (!isoString) return '—';
  const diff = Math.floor((Date.now() - new Date(isoString)) / 1000);
  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  if (diff < 86400)return `${Math.floor(diff/3600)}h ago`;
  return new Date(isoString).toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' });
}

function badge(cls, text) {
  return `<span class="badge badge-${cls}">${text}</span>`;
}

// ── Tab switching ──────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab' + name.charAt(0).toUpperCase() + name.slice(1)).classList.remove('hidden');
  event.currentTarget.classList.add('active');

  if (name === 'deals')  loadDeals();
  if (name === 'orders') loadOrders();
}

// ── Stats ──────────────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const res = await fetch(API.dashboard);
    if (res.status === 401 || res.status === 403) {
      showAuthError();
      return;
    }
    const d = await res.json();
    document.getElementById('statDeals').textContent   = d.total_deals;
    document.getElementById('statActive').textContent  = d.active_sessions;
    document.getElementById('statOrders').textContent  = d.total_orders;
    document.getElementById('statRevenue').textContent = inr(d.total_revenue);
  } catch (e) {
    console.error('Stats error:', e);
  }
}

// ── Deals table ────────────────────────────────────────────────────────────
async function loadDeals() {
  const tbody = document.getElementById('dealsTbody');
  tbody.innerHTML = '<tr><td colspan="10" class="loading">Loading deals…</td></tr>';

  try {
    const res = await fetch(API.deals);
    if (res.status === 401 || res.status === 403) { showAuthError(); return; }
    const deals = await res.json();

    if (!deals.length) {
      tbody.innerHTML = '<tr><td colspan="10" class="empty">🤝 No confirmed deals yet</td></tr>';
      return;
    }

    tbody.innerHTML = deals.map(d => `
      <tr>
        <td><strong>#${d.session_id}</strong></td>
        <td>
          <strong>${escHtml(d.product_name)}</strong>
        </td>
        <td>
          <div class="buyer-name">${escHtml(d.buyer_name)}</div>
          <div class="buyer-email">${escHtml(d.buyer_email)}</div>
        </td>
        <td>${d.quantity}</td>
        <td class="price-orig">${inr(d.original_price)}</td>
        <td class="price-deal">${inr(d.final_price)}</td>
        <td><strong>${inr(d.total_value)}</strong></td>
        <td class="price-saved">-${inr(Math.max(d.saved, 0))}</td>
        <td>${d.rounds_used} / ${d.max_rounds}</td>
        <td>${badge('confirmed', 'Confirmed')}</td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty">⚠️ Failed to load deals</td></tr>`;
    console.error(e);
  }
}

// ── Orders table ───────────────────────────────────────────────────────────
async function loadOrders() {
  const tbody = document.getElementById('ordersTbody');
  tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading orders…</td></tr>';

  try {
    const res = await fetch(API.orders);
    if (res.status === 401 || res.status === 403) { showAuthError(); return; }
    const orders = await res.json();

    if (!orders.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">📦 No orders placed yet</td></tr>';
      return;
    }

    tbody.innerHTML = orders.map(o => {
      const itemList = o.items.map(i =>
        `${escHtml(i.product_name)} ×${i.quantity} @ ${inr(i.price_per_unit)}`
      ).join('<br>');
      const statusClass = o.status === 'PLACED' ? 'placed' : 'closed';
      return `
        <tr>
          <td><strong>#${o.order_id}</strong></td>
          <td class="buyer-name">${escHtml(o.buyer_name)}</td>
          <td class="buyer-email">${escHtml(o.buyer_email)}</td>
          <td style="font-size:.82rem;line-height:1.6">${itemList}</td>
          <td><strong>${inr(o.total)}</strong></td>
          <td>${badge(statusClass, o.status)}</td>
          <td style="white-space:nowrap;font-size:.82rem;color:#555">${timeAgo(o.placed_at)}</td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">⚠️ Failed to load orders</td></tr>`;
    console.error(e);
  }
}

// ── Auth error ─────────────────────────────────────────────────────────────
function showAuthError() {
  document.querySelector('.page').innerHTML = `
    <div style="text-align:center;padding:4rem 1rem">
      <div style="font-size:3rem">🔒</div>
      <h2 style="margin:.8rem 0 .5rem">Admin Access Only</h2>
      <p style="color:#777;margin-bottom:1.5rem">You need to be logged in as an admin to view the Seller Dashboard.</p>
      <a href="/login" style="background:#1a1a2e;color:#f9a825;padding:.7rem 2rem;border-radius:8px;text-decoration:none;font-weight:700">Login</a>
    </div>`;
}

// ── XSS helper ─────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

// ── Init ───────────────────────────────────────────────────────────────────
loadStats();
loadDeals();

// Auto-refresh stats every 30 seconds
setInterval(loadStats, 30_000);
