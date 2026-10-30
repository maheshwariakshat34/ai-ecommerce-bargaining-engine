/* seller.js — Complete Unified Seller & Inventory Dashboard */

const API = {
  dashboard: '/api/seller/dashboard',
  deals:     '/api/seller/deals',
  orders:    '/api/seller/orders',
  products:  '/api/products?view=admin',
  clearance: '/api/clearance/',
  productSave: '/api/products',
  logout:    '/api/auth/logout'
};

const FIELDS = [
  ['name', 'Product Name', 'text'],
  ['category', 'Category', 'text'],
  ['base_price', 'Base Price (₹)', 'number'],
  ['cost_price', 'Cost Price (₹)', 'number'],
  ['minimum_price', 'Minimum Floor Price (₹)', 'number'],
  ['stock', 'Stock Units', 'number'],
  ['inventory_age', 'Inventory Age (Days)', 'number'],
  ['expiry_date', 'Expiry Date (optional)', 'date'],
  ['sales_last_7_days', 'Sales Last 7 Days', 'number'],
  ['sales_last_30_days', 'Sales Last 30 Days', 'number'],
  ['demand_level', 'Demand Level', 'select'],
  ['seasonal_factor', 'Seasonal Factor (-1 to 1)', 'number'],
  ['image_url', 'Photo Path / Link', 'text']
];

let productList = [];
let editingProductId = null;

// ── Helpers ────────────────────────────────────────────────────────────────
function inr(n) {
  if (n === null || n === undefined || isNaN(n)) return '—';
  return '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
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

  const paneId = 'tab' + name.charAt(0).toUpperCase() + name.slice(1);
  const pane = document.getElementById(paneId);
  if (pane) pane.classList.remove('hidden');

  const btnId = 'tabBtn' + name.charAt(0).toUpperCase() + name.slice(1);
  const btn = document.getElementById(btnId);
  if (btn) btn.classList.add('active');

  if (name === 'deals')    loadDeals();
  if (name === 'orders')   loadOrders();
  if (name === 'products') loadProducts();
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
      tbody.innerHTML = '<tr><td colspan="10" class="empty">🤝 No confirmed bargaining deals yet</td></tr>';
      return;
    }

    tbody.innerHTML = deals.map(d => `
      <tr>
        <td><strong>#${d.session_id}</strong></td>
        <td><strong>${escHtml(d.product_name)}</strong></td>
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
      tbody.innerHTML = '<tr><td colspan="7" class="empty">📦 No customer orders placed yet</td></tr>';
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

// ── Products & Inventory ───────────────────────────────────────────────────
async function loadProducts() {
  const tbody = document.getElementById('productsTbody');
  tbody.innerHTML = '<tr><td colspan="11" class="loading">Loading products…</td></tr>';

  try {
    const res = await fetch(API.products);
    if (res.status === 401 || res.status === 403) { showAuthError(); return; }
    productList = await res.json();

    document.getElementById('prodCount').textContent = `${productList.length} products`;

    if (!productList.length) {
      tbody.innerHTML = '<tr><td colspan="11" class="empty">No products found. Add your first product!</td></tr>';
      return;
    }

    // Fetch clearance data in parallel
    const clearances = await Promise.all(
      productList.map(p => fetch(API.clearance + p.id).then(r => r.json()).catch(() => ({})))
    );

    tbody.innerHTML = productList.map((p, idx) => {
      const c = clearances[idx]?.clearance || {};
      const expDays = p.days_to_expiry;
      const expText = expDays == null ? '—' : expDays <= 0 ? '❌ Expired' : `${expDays} d`;
      const level = c.clearance_level || 'NORMAL';
      const disc = c.discount_percent != null ? `${c.discount_percent}%` : '0%';

      return `
        <tr>
          <td><strong>${escHtml(p.name)}</strong></td>
          <td>${escHtml(p.category)}</td>
          <td>${inr(p.base_price)}</td>
          <td>${inr(p.cost_price)}</td>
          <td>${inr(p.minimum_price)}</td>
          <td><strong>${p.stock}</strong></td>
          <td style="font-size:0.8rem">${expText}</td>
          <td style="font-weight:700;color:#2e7d32">${c.clearance_price != null ? inr(c.clearance_price) : inr(p.base_price)}</td>
          <td style="font-weight:600;color:#e53935">${disc}</td>
          <td>
            <span class="level-badge level-${level}" title="${escHtml((c.reasons || []).join(', '))}">
              ${level}
            </span>
          </td>
          <td>
            <button class="btn-edit" onclick="openProductModal(${p.id})">Edit</button>
            <button class="btn-del" onclick="deleteProduct(${p.id})">Delete</button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="11" class="empty">⚠️ Failed to load products</td></tr>`;
    console.error(e);
  }
}

// ── Add / Edit Product Modal ───────────────────────────────────────────────
function openProductModal(prodId) {
  editingProductId = prodId;
  const prod = prodId ? productList.find(x => x.id === prodId) : null;

  document.getElementById('modalTitle').textContent = prod ? 'Edit Product & Pricing' : 'Add New Product';
  document.getElementById('formError').textContent = '';

  const form = document.getElementById('productForm');
  form.innerHTML = FIELDS.map(([k, label, type]) => {
    let inputHtml = '';
    const currentVal = prod ? (prod[k] ?? '') : '';

    if (type === 'select') {
      const options = ['LOW', 'MEDIUM', 'HIGH'].map(opt =>
        `<option value="${opt}" ${currentVal === opt ? 'selected' : ''}>${opt}</option>`
      ).join('');
      inputHtml = `<select id="f_${k}">${options}</select>`;
    } else {
      inputHtml = `<input id="f_${k}" type="${type}" step="any" value="${escHtml(currentVal)}">`;
    }

    return `
      <div>
        <label for="f_${k}">${label}</label>
        ${inputHtml}
      </div>
    `;
  }).join('');

  document.getElementById('productModal').hidden = false;
}

function closeProductModal() {
  document.getElementById('productModal').hidden = true;
  editingProductId = null;
}

async function saveProduct() {
  const errEl = document.getElementById('formError');
  errEl.textContent = '';

  const payload = {};
  for (const [k, , type] of FIELDS) {
    const raw = document.getElementById('f_' + k).value.trim();
    if (type === 'number') {
      payload[k] = raw === '' ? null : Number(raw);
    } else {
      payload[k] = raw;
    }
  }

  // Cost and min price validation
  if (payload.cost_price > payload.minimum_price || payload.minimum_price > payload.base_price) {
    errEl.textContent = 'Rule violation: Cost Price ≤ Minimum Price ≤ Base Price.';
    return;
  }

  try {
    const url = editingProductId ? `${API.productSave}/${editingProductId}` : API.productSave;
    const method = editingProductId ? 'PUT' : 'POST';

    const res = await fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      errEl.textContent = data.message || data.error || 'Failed to save product.';
      return;
    }

    closeProductModal();
    loadProducts();
  } catch (err) {
    errEl.textContent = 'Server connection error.';
  }
}

async function deleteProduct(id) {
  if (!confirm('Are you sure you want to delete this product?')) return;
  try {
    const res = await fetch(`${API.productSave}/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) {
      alert(data.message || data.error || 'Failed to delete product.');
      return;
    }
    loadProducts();
  } catch (e) {
    alert('Server connection error.');
  }
}

// ── Auth error ─────────────────────────────────────────────────────────────
function showAuthError() {
  document.querySelector('.page').innerHTML = `
    <div style="text-align:center;padding:4rem 1rem">
      <div style="font-size:3rem">🔒</div>
      <h2 style="margin:.8rem 0 .5rem">Seller / Admin Access Only</h2>
      <p style="color:#777;margin-bottom:1.5rem">You need to be logged in as the seller/admin to view this dashboard.</p>
      <a href="/login" style="background:#1a1a2e;color:#f9a825;padding:.7rem 2rem;border-radius:8px;text-decoration:none;font-weight:700">Login as Seller</a>
    </div>`;
}

async function logoutSeller() {
  await fetch(API.logout, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  window.location.assign('/');
}

// ── Init ───────────────────────────────────────────────────────────────────
loadStats();
loadDeals();

// Auto-refresh stats every 30 seconds
setInterval(loadStats, 30_000);
