const IMAGES = {
    "Wireless Headphones": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=max&w=600&q=80",
    "Smart Watch": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=max&w=600&q=80",
    "Sports Shoes": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=max&w=600&q=80",
    "Bluetooth Speaker":"https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?&auto=format&fit=max&w=600&q=80",
    "Old Model Tablet":"https://images.unsplash.com/photo-1766241632392-1c84994a5e62?&auto=format&fit=max&w=600&q=80",
    "USB-C Cable (1m)":"https://images.unsplash.com/photo-1639675960002-2f414c58ed79?&auto=format&fit=max&w=600&q=80",
    "Power Bank 10000mAh":"https://images.unsplash.com/photo-1614399113305-a127bb2ca893?&auto=format&fit=max&w=600&q=80",
    "Winter Boots":"https://plus.unsplash.com/premium_photo-1729788891863-0d9b6f2b453b?&auto=format&fit=max&w=600&q=80",
    "Running Shoes Pro":"https://images.unsplash.com/photo-1491553895911-0055eca6402d?q=80&w=600&auto=format&fit=max",
    "Flip Flops":"images/flipflop.jpg",
    "Cotton T-Shirt":"images/shirt.jpg",
    "Denim Jeans":"images/jean.jpg",
    "Woolen Sweater":"images/sweater.jpg",
    "Hooded Jacket":"https://plus.unsplash.com/premium_photo-1673356302125-c77491af8735?q=80&w=687&auto=format&fit=max",
    "Cotton Socks (pair)":"images/socks.jpg",
    "Protein Bar":"https://images.unsplash.com/photo-1742860866012-fc167d8366bf?w=600&auto=format&fit=max&q=80",
    "Fresh Orange Juice":"https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=600&auto=format&fit=max&q=80",
    "Basmati Rice 5kg":"https://images.unsplash.com/photo-1625827626291-6fbd47a431ae?w=600&auto=format&fit=max&q=80",
    "Cream Biscuits":"https://plus.unsplash.com/premium_photo-1663046012412-a9a08b88ddcd?w=600&auto=format&fit=max&q=80",
    "Green Tea (100 bags)":"https://images.unsplash.com/photo-1597066371673-2088a5c19802?w=600&auto=format&fit=max&q=80",
    "Non-stick Pan":"https://images.unsplash.com/photo-1592156328757-ae2941276b2c?w=600&auto=format&fit=max&q=80",
    "Electric Kettle":"https://images.unsplash.com/photo-1738520420652-0c47cea3922b?q=80&w=600&auto=format&fit=max",
    "LED Desk Lamp":"https://images.unsplash.com/photo-1731762524352-b5663f83a830?w=600&auto=format&fit=max&q=80",
    "Face Moisturizer":"images/facewash.jpg",
    "Shampoo 500ml":"https://images.unsplash.com/photo-1747858989102-cca0f4dc4a11?w=600&auto=format&fit=max&q=80",
    "Yoga Mat":"images/yogamat.jpg",
    "Cricket Bat":"images/bat.jpg",
    "Notebook (pack of 5)":"https://images.unsplash.com/photo-1624627274968-0fd0ab784a78?q=80&w=600&auto=format&fit=max",
    "Fresh Bread Loaf":"https://images.unsplash.com/photo-1598373182308-3270495d2f58?q=80&w=600&auto=format&fit=max",
    "Expired Yogurt Cup":"https://images.unsplash.com/photo-1604095853918-1a1823a63dd5?q=80&w=600&auto=format&fit=max",





};

// products without a photo show an emoji of their category
const CATEGORY_ICONS = {
    Electronics: "🎧", Footwear: "👟", Clothing: "👕", Food: "🍫",
    "Home & Kitchen": "🏠", Beauty: "💄", Sports: "🏏", Stationery: "📓"
};

// a nicer emoji for each product (used when there is no photo)
const PRODUCT_ICONS = {
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

function $(id) {
    return document.getElementById(id);
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function formatPrice(price) {
    return "₹" + Number(price).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function scrollToElement(element) {
    if (element && element.scrollIntoView) {
        element.scrollIntoView({ behavior: "smooth" });
    }
}

let toastTimer;

function showToast(text) {
    const toast = $("toast");
    if (!toast) return;

    toast.textContent = text;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
        toast.hidden = true;
    }, 2500);
}

// sends json to the backend and gives back ok, status and the json reply
async function post(path, body) {
    const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });

    let data = {};
    try {
        data = await response.json();
    } catch (error) {
        // reply had no json, keep data empty
    }

    return { ok: response.ok, status: response.status, data: data };
}

function setOnline(online) {
    if (!$("statusText")) return;

    $("statusText").textContent = online ? "Online" : "Offline";
    $("statusLine").classList.toggle("offline", !online);
}

function bargainUrl(product) {
    return "/bargain?product=" + product.id;
}

// update cart badge in the navbar (called from bargain.js after deal accepted)
function updateCartBadge(count) {
    let badge = $("cartBadge");
    if (!badge) return;
    badge.textContent = count;
    badge.hidden = count === 0;
}

function isClearance(product) {
    return product.discount_percent > 0;
}

// small tag on the product photo
function badgeFor(product) {
    if (product.discount_percent >= 20) {
        return { text: "Clearance", color: "red" };
    }
    if (product.discount_percent > 0) {
        return { text: Math.round(product.discount_percent) + "% OFF", color: "green" };
    }
    return null;
}

// "Expires in 5 days" for products that expire within a month
function expiryText(product) {
    const days = product.days_to_expiry;

    if (days === null || days === undefined || days > 30) return "";
    // BUG 10 FIX: days==0 means "expires today", days<0 means already expired.
    // Previously both showed "Expires tomorrow" which was wrong.
    if (days <= 0) return "Expires today";
    if (days === 1) return "Expires tomorrow";
    return "Expires in " + days + " days";
}

function expiryNoteHtml(product) {
    const text = expiryText(product);
    if (!text) return "";

    return '<p class="expiry-note" style="margin:0 0 6px;font-size:12px;' +
        'font-weight:600;color:#b45309">⏳ ' + text + "</p>";
}

function thumbHtml(product) {
    const icon = PRODUCT_ICONS[product.name] || CATEGORY_ICONS[product.category] || "🛍️";

    // photo from the database (image_url) first, then the built-in list above
    const image = product.image_url || IMAGES[product.name];

    if (image) {
        return '<img src="' + escapeHtml(image) + '" alt="' + escapeHtml(product.name) +
            '" data-icon="' + icon + '">';
    }

    return '<div class="thumb-fallback">' + icon + "</div>";
}

// if a photo does not load, show an emoji instead
document.addEventListener("error", function (event) {
    if (event.target.tagName !== "IMG") return;

    const fallback = document.createElement("div");
    fallback.className = "thumb-fallback";
    fallback.textContent = event.target.dataset.icon || "🛍️";

    // tells you WHICH photo failed: see the browser console (F12), or hover the emoji
    const failed = event.target.getAttribute("src");
    console.warn("Photo could not load:", failed);
    fallback.title = "Photo could not load: " + failed;

    event.target.replaceWith(fallback);
}, true);


// ---------- logged in user ----------
// The server knows who is logged in (a cookie). loadSession() asks it and fills the navbar.

let currentUser = { name: "Guest", guest: true, role: null };
let loginRequired = false;   // the shop wants a login before bargaining

async function loadSession() {
    try {
        const response = await fetch("/api/auth/me");
        const data = await response.json();

        loginRequired = Boolean(data.login_required_to_bargain);
        currentUser = data.user
            ? { name: data.user.name, guest: false, role: data.user.role }
            : { name: "Guest", guest: true, role: null };
    } catch (error) {
        currentUser = { name: "Guest", guest: true, role: null };
    }

    showUser();
}

// login page that brings the person back here, like /login?next=/bargain%3Fproduct%3D3
function loginUrl() {
    const page = window.location.pathname + window.location.search;
    const skip = !page || page === "/" || page.startsWith("/login");

    return "/login" + (skip ? "" : "?next=" + encodeURIComponent(page));
}

function showUser() {
    $("userName").textContent = currentUser.name;
    $("userAvatar").textContent = currentUser.name.charAt(0).toUpperCase();
    $("authBtn").textContent = currentUser.guest ? "Log in" : "Log out";
    $("userLine").textContent = currentUser.guest
        ? "You are browsing as a guest."
        : "Signed in as " + currentUser.name + (currentUser.role === "admin" ? " (seller)" : "");

    // the seller gets a link to the dashboard
    let dashboard = $("dashboardBtn");

    if (currentUser.role === "admin" && !dashboard) {
        dashboard = document.createElement("button");
        dashboard.type = "button";
        dashboard.id = "dashboardBtn";
        dashboard.textContent = "Seller dashboard";
        dashboard.addEventListener("click", function () {
            window.location.assign("/admin");
        });
        $("userDropdown").insertBefore(dashboard, $("authBtn"));
    } else if (currentUser.role !== "admin" && dashboard) {
        dashboard.remove();
    }
}

// the navbar is the same on every page, so it is set up here
async function initNavbar() {
    showUser();

    $("userBtn").addEventListener("click", function (event) {
        event.stopPropagation();
        $("userDropdown").hidden = !$("userDropdown").hidden;
    });

    document.addEventListener("click", function (event) {
        if (!event.target.closest("#userMenu")) {
            $("userDropdown").hidden = true;
        }

        const orders = event.target.closest('[data-nav="orders"]');
        if (orders) {
            event.preventDefault();
            window.location.assign("/orders");
        }
    });

    $("authBtn").addEventListener("click", async function () {
        $("userDropdown").hidden = true;

        if (currentUser.guest) {
            window.location.assign(loginUrl());
            return;
        }

        await post("/api/auth/logout", {});
        showToast("You have been logged out.");
        setTimeout(function () {
            window.location.assign("/");
        }, 600);
    });

    $("ordersBtn").addEventListener("click", function () {
        $("userDropdown").hidden = true;
        window.location.assign("/orders");
    });

    $("bellBtn").addEventListener("click", function () {
        showToast("No new notifications.");
    });

    await loadSession();
}
