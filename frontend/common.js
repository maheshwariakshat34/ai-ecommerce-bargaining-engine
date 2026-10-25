// code used by every page (home page and bargain page)

const IMAGES = {
    "Wireless Headphones": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80",
    "Smart Watch": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80",
    "Sports Shoes": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80"
};

// products without a photo show an emoji of their category
const CATEGORY_ICONS = { Electronics: "🎧", Footwear: "👟", Clothing: "👕", Food: "🍫" };

const USER_KEY = "smartshop_user";

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
    return "bargain.html?product=" + product.id;
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

function thumbHtml(product) {
    const image = IMAGES[product.name];

    if (image) {
        return '<img src="' + image + '" alt="' + escapeHtml(product.name) + '">';
    }

    const icon = CATEGORY_ICONS[product.category] || "🛍️";
    return '<div class="thumb-fallback">' + icon + "</div>";
}

// if a photo does not load, show an emoji instead
document.addEventListener("error", function (event) {
    if (event.target.tagName !== "IMG") return;

    const fallback = document.createElement("div");
    fallback.className = "thumb-fallback";
    fallback.textContent = "🛍️";
    event.target.replaceWith(fallback);
}, true);


// ---------- logged in user ----------
// Everyone is a guest for now. When login is added, call
// setCurrentUser({ name: "Akshat" }) after login and the name shows up.
// To try it now, open any page with ?user=Akshat

const urlParams = new URLSearchParams(window.location.search);

if (urlParams.get("user")) {
    localStorage.setItem(USER_KEY, JSON.stringify({ name: urlParams.get("user").slice(0, 40) }));
    urlParams.delete("user");

    const rest = urlParams.toString();
    window.history.replaceState(null, "", window.location.pathname + (rest ? "?" + rest : ""));
}

function loadCurrentUser() {
    try {
        const saved = JSON.parse(localStorage.getItem(USER_KEY));
        if (saved && saved.name) {
            return { name: saved.name, guest: false };
        }
    } catch (error) {
        // saved value was broken, treat as guest
    }
    return { name: "Guest", guest: true };
}

let currentUser = loadCurrentUser();

function setCurrentUser(user) {
    if (user && user.name) {
        localStorage.setItem(USER_KEY, JSON.stringify({ name: user.name }));
    } else {
        localStorage.removeItem(USER_KEY);
    }

    currentUser = loadCurrentUser();
    showUser();
}

function showUser() {
    $("userName").textContent = currentUser.name;
    $("userAvatar").textContent = currentUser.name.charAt(0).toUpperCase();
    $("authBtn").textContent = currentUser.guest ? "Log in" : "Log out";
    $("userLine").textContent = currentUser.guest
        ? "You are browsing as a guest."
        : "Signed in as " + currentUser.name;
}

// the navbar is the same on every page, so it is set up here
function initNavbar() {
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
            showToast("My Orders will be available once ordering is added.");
        }
    });

    $("authBtn").addEventListener("click", function () {
        $("userDropdown").hidden = true;

        if (currentUser.guest) {
            showToast("Login will be available soon.");
        } else {
            setCurrentUser(null);
            showToast("You have been logged out.");
        }
    });

    $("ordersBtn").addEventListener("click", function () {
        $("userDropdown").hidden = true;
        showToast("My Orders will be available once ordering is added.");
    });

    $("bellBtn").addEventListener("click", function () {
        showToast("No new notifications.");
    });
}