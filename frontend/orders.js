/* orders.js — cart & order history page logic */

"use strict";


const ICONS = {
    "Wireless Headphones": "🎧", "Smart Watch": "⌚", "Sports Shoes": "👟",
    "Bluetooth Speaker": "🔊", "Old Model Tablet": "📱", "USB-C Cable (1m)": "🔌",
    "Power Bank 10000mAh": "🔋", "Winter Boots": "🥾", "Running Shoes Pro": "👟",
    "Flip Flops": "🩴", "Cotton T-Shirt": "👕", "Denim Jeans": "👖",
    "Woolen Sweater": "🧶", "Hooded Jacket": "🧥", "Cotton Socks (pair)": "🧦",
    "Protein Bar": "🍫", "Fresh Orange Juice": "🧃", "Basmati Rice 5kg": "🍚",
    "Cream Biscuits": "🍪", "Green Tea (100 bags)": "🍵", "Fresh Bread Loaf": "🍞",
    "Non-stick Pan": "🍳", "Electric Kettle": "🫖", "LED Desk Lamp": "💡",
    "Face Moisturizer": "🧴", "Shampoo 500ml": "🧴", "Yoga Mat": "🧘",
    "Cricket Bat": "🏏", "Notebook (pack of 5)": "📓"
};

function iconFor(name) {
    return ICONS[name] || "🛍️";
}

function inr(n) {
    return "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function fmtDate(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

// ── cart ────────────────────────────────────────────────────────────
async function loadCart() {
    const loading = $("cartLoading");
    const empty   = $("cartEmpty");
    const items   = $("cartItems");
    const prompt  = $("cartLoginPrompt");

    loading.hidden = false;
    empty.hidden = true;
    items.hidden = true;
    prompt.hidden = true;

    try {
        const res  = await fetch("/api/cart");
        const data = await res.json();

        loading.hidden = true;

        if (res.status === 401) {
            prompt.hidden = false;
            return;
        }

        if (!res.ok || !data.items || data.items.length === 0) {
            empty.hidden = false;
            return;
        }

        renderCart(data);
        items.hidden = false;
    } catch (err) {
        loading.hidden = true;
        empty.hidden = false;
    }
}

function renderCart(data) {
    const list = $("cartList");
    list.innerHTML = "";

    data.items.forEach(function (item) {
        const card = document.createElement("div");
        card.className = "cart-item";
        card.id = "cartItem-" + item.id;

        const saved = Math.max(item.saved || 0, 0);
        const badgeHtml = saved > 0
            ? `<span class="cart-item-badge">Saved ${inr(saved)} via bargain 🎉</span>`
            : "";

        card.innerHTML = `
            <div class="cart-item-icon">${iconFor(item.product_name)}</div>
            <div class="cart-item-info">
                <div class="cart-item-name">${escapeHtml(item.product_name)}</div>
                <div class="cart-item-meta">Qty: ${item.quantity} × ${inr(item.price_per_unit)}</div>
                ${badgeHtml}
            </div>
            <div class="cart-item-price">
                ${item.original_price > item.price_per_unit
                    ? `<div class="cart-item-original">${inr(item.original_price * item.quantity)}</div>`
                    : ""}
                <div class="cart-item-total">${inr(item.total)}</div>
            </div>
            <button class="remove-btn" title="Remove item" data-id="${item.id}">✕</button>
        `;

        card.querySelector(".remove-btn").addEventListener("click", function () {
            removeItem(item.id);
        });

        list.appendChild(card);
    });

    // summary
    $("summaryCount").textContent = data.count + (data.count === 1 ? " item" : " items");
    $("summaryTotal").textContent = inr(data.total);
    $("summarySaved").textContent = inr(data.total_saved || 0);
}

async function removeItem(itemId) {
    const card = $("cartItem-" + itemId);
    if (card) {
        card.style.opacity = "0.4";
        card.style.pointerEvents = "none";
    }

    try {
        const res  = await fetch("/api/cart/" + itemId, { method: "DELETE" });
        const data = await res.json();

        if (res.ok) {
            showToast("Item removed from cart.");
            await loadCart();
        } else {
            showToast(data.error || "Could not remove item.");
            if (card) { card.style.opacity = ""; card.style.pointerEvents = ""; }
        }
    } catch (err) {
        showToast("Could not reach the server.");
        if (card) { card.style.opacity = ""; card.style.pointerEvents = ""; }
    }
}

// ── place order ─────────────────────────────────────────────────────
async function placeOrder() {
    const btn = $("placeOrderBtn");
    btn.disabled = true;
    btn.textContent = "Placing order…";

    try {
        const res  = await fetch("/api/orders/place", { method: "POST" });
        const data = await res.json();

        if (res.ok) {
            // show success modal
            $("modalMsg").textContent =
                "Order #" + data.order.id + " placed for " + inr(data.order.total) + ". We'll prepare it right away!";
            $("successModal").hidden = false;
        } else {
            showToast(data.error || "Could not place order.");
            btn.disabled = false;
            btn.textContent = "Place Order →";
        }
    } catch (err) {
        showToast("Could not reach the server.");
        btn.disabled = false;
        btn.textContent = "Place Order →";
    }
}

// ── order history ───────────────────────────────────────────────────
async function loadHistory() {
    const loading = $("historyLoading");
    const empty   = $("historyEmpty");
    const list    = $("orderList");
    const prompt  = $("historyLoginPrompt");

    loading.hidden = false;
    empty.hidden   = true;
    list.hidden    = true;
    prompt.hidden  = true;

    try {
        const res  = await fetch("/api/orders");
        const data = await res.json();

        loading.hidden = true;

        if (res.status === 401) {
            prompt.hidden = false;
            return;
        }

        if (!res.ok || !data.orders || data.orders.length === 0) {
            empty.hidden = false;
            return;
        }

        renderHistory(data.orders);
        list.hidden = false;
    } catch (err) {
        loading.hidden = true;
        empty.hidden   = false;
    }
}

function renderHistory(orders) {
    const list = $("orderList");
    list.innerHTML = "";

    orders.forEach(function (order) {
        const card = document.createElement("div");
        card.className = "order-card";

        const itemLines = order.items.map(function (item) {
            return `
                <div class="order-line">
                    <span class="order-line-name">${escapeHtml(item.product_name)}</span>
                    <span class="order-line-qty">× ${item.quantity}</span>
                    <span class="order-line-price">${inr(item.total)}</span>
                </div>`;
        }).join("");

        card.innerHTML = `
            <div class="order-card-header">
                <span class="order-id">Order #${order.id}</span>
                <span class="order-date">${fmtDate(order.placed_at)}</span>
                <span class="order-status">${order.status}</span>
            </div>
            <div class="order-items-list">${itemLines}</div>
            <div class="order-card-footer">
                <span class="order-total-label">Order Total</span>
                <span class="order-total-amount">${inr(order.total)}</span>
            </div>`;

        list.appendChild(card);
    });
}

// ── tabs ────────────────────────────────────────────────────────────
function switchTab(tab) {
    const isCart = tab === "cart";

    $("tabCart").classList.toggle("active", isCart);
    $("tabHistory").classList.toggle("active", !isCart);
    $("cartSection").hidden    = !isCart;
    $("historySection").hidden = isCart;

    if (!isCart) loadHistory();
}

// ── init ────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async function () {
    await initNavbar();

    $("tabCart").addEventListener("click", function () { switchTab("cart"); });
    $("tabHistory").addEventListener("click", function () { switchTab("history"); });

    $("placeOrderBtn").addEventListener("click", placeOrder);

    $("modalViewOrders").addEventListener("click", function () {
        $("successModal").hidden = true;
        switchTab("history");
        loadHistory();
    });

    // load cart on startup
    loadCart();
});
