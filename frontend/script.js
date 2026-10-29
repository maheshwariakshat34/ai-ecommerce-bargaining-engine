// home page: products, clearance deals and the helper assistant
// (the bargaining chat itself is on bargain.html)

const searchInput = $("searchInput");
const productGrid = $("productGrid");
const emptyMessage = $("emptyMessage");
const chatLog = $("chatLog");
const messageInput = $("messageInput");

let products = [];
let view = "featured";   // featured, all or clearance


// ---------- products ----------

async function loadProducts() {
    try {
        const response = await fetch("/api/products");
        if (!response.ok) throw new Error("bad response");

        products = await response.json();
        setOnline(true);
        showAll();
    } catch (error) {
        products = [];
        setOnline(false);
        showAll();
        emptyMessage.textContent = "Could not load products. Is the server running?";
        emptyMessage.hidden = false;
    }
}

// one product from each category first, so the home page shows a mix
function pickFeatured() {
    const inStock = products.filter(function (p) { return p.stock > 0; });
    const picked = [];
    const seen = {};

    inStock.forEach(function (p) {
        if (picked.length < 4 && !seen[p.category]) {
            seen[p.category] = true;
            picked.push(p);
        }
    });

    inStock.forEach(function (p) {
        if (picked.length < 4 && picked.indexOf(p) === -1) picked.push(p);
    });

    return picked;
}

function getVisibleProducts() {
    const text = searchInput.value.trim().toLowerCase();

    if (text) {
        return products.filter(function (p) {
            return p.name.toLowerCase().includes(text) ||
                   p.category.toLowerCase().includes(text);
        });
    }

    if (view === "clearance") {
        return products.filter(isClearance);
    }
    if (view === "featured") {
        return pickFeatured();
    }
    return products;
}

function showProducts() {
    const searching = searchInput.value.trim() !== "";
    const list = getVisibleProducts();

    const titles = {
        featured: "Featured Products",
        all: "All Products",
        clearance: "Clearance Deals"
    };
    $("sectionTitle").textContent = searching ? "Search Results" : titles[view];

    $("viewAllBtn").hidden = searching;
    $("viewAllBtn").textContent = view === "featured" ? "View All ›" : "Show Featured ›";

    emptyMessage.textContent = "No products found. Try another search.";
    emptyMessage.hidden = list.length !== 0;

    let html = "";

    list.forEach(function (product) {
        const badge = badgeFor(product);
        let badgeHtml = "";
        let oldPrice = "";
        let button = '<button class="bargain-btn" data-product-id="' + product.id + '">🛒 Bargain Now</button>';

        if (badge) {
            badgeHtml = '<span class="badge ' + badge.color + '">' + badge.text + "</span>";
        }
        if (isClearance(product)) {
            oldPrice = '<span class="old-price">' + formatPrice(product.base_price) + "</span>";
        }
        if (product.stock <= 0) {
            button = '<button class="bargain-btn" disabled>Out of stock</button>';
        }

        html += '<article class="product-card">' +
            '<div class="product-image">' + badgeHtml + thumbHtml(product) + "</div>" +
            '<h3 class="product-name">' + escapeHtml(product.name) + "</h3>" +
            expiryNoteHtml(product) +
            '<div class="price-row">' + oldPrice +
            '<span class="current-price">' + formatPrice(product.price) + "</span></div>" +
            button +
            "</article>";
    });

    productGrid.innerHTML = html;
}

function showClearance() {
    const deals = products
        .filter(function (p) { return isClearance(p) && p.stock > 0; })
        .sort(function (a, b) { return b.discount_percent - a.discount_percent; })
        .slice(0, 3);

    if (deals.length === 0) {
        $("clearanceList").innerHTML = '<p class="clearance-empty">No clearance deals right now.</p>';
        return;
    }

    let html = "";

    deals.forEach(function (product) {
        html += '<button class="clearance-item" type="button" data-product-id="' + product.id + '">' +
            '<span class="clearance-thumb">' + thumbHtml(product) + "</span>" +
            '<span class="clearance-info">' +
            '<span class="clearance-name">' + escapeHtml(product.name) + "</span>" +
            '<span class="off-pill">' + Math.round(product.discount_percent) + "% OFF</span>" +
            '<span class="stock-left">Only ' + product.stock + " left" +
            (expiryText(product) ? " · " + expiryText(product) : "") + "</span>" +
            "</span><span>›</span></button>";
    });

    $("clearanceList").innerHTML = html;
}

function showAll() {
    showProducts();
    showClearance();
}

function changeView(newView) {
    view = newView;
    searchInput.value = "";
    showProducts();
}

function setActiveNav(name) {
    document.querySelectorAll("#mainNav a").forEach(function (link) {
        link.classList.toggle("active", link.dataset.nav === name);
    });
}

function openBargainPage(product) {
    window.location.assign(bargainUrl(product));
}

// finds the product whose button was clicked
function getClickedProduct(event) {
    const button = event.target.closest("[data-product-id]");
    if (!button || button.disabled) return null;

    return products.find(function (p) {
        return p.id === Number(button.dataset.productId);
    });
}

productGrid.addEventListener("click", function (event) {
    const product = getClickedProduct(event);
    if (product) openBargainPage(product);
});

$("clearanceList").addEventListener("click", function (event) {
    const product = getClickedProduct(event);
    if (product) openBargainPage(product);
});

searchInput.addEventListener("input", showProducts);

$("viewAllBtn").addEventListener("click", function () {
    changeView(view === "featured" ? "all" : "featured");
    setActiveNav(view === "all" ? "products" : "home");
});

$("clearanceAllBtn").addEventListener("click", function () {
    changeView("clearance");
    setActiveNav("clearance");
    scrollToElement($("products"));
});

// navbar links
document.addEventListener("click", function (event) {
    const link = event.target.closest("[data-nav]");
    if (!link) return;

    const name = link.dataset.nav;
    if (name === "orders") return;   // handled in common.js

    event.preventDefault();

    if (name === "home") {
        changeView("featured");
        setActiveNav("home");
        window.scrollTo({ top: 0, behavior: "smooth" });
    } else if (name === "products") {
        changeView("all");
        setActiveNav("products");
        scrollToElement($("products"));
    } else if (name === "clearance") {
        changeView("clearance");
        setActiveNav("clearance");
        scrollToElement($("products"));
    } else if (name === "bargain") {
        setActiveNav("bargain");
        startBargaining();
        scrollToElement($("assistant"));
    }
});

$("heroBtn").addEventListener("click", function () {
    startBargaining();
    scrollToElement($("assistant"));
});


// ---------- helper assistant ----------

function addMessage(kind, text, extra) {
    const box = document.createElement("div");
    const bubble = document.createElement("div");

    box.className = "msg " + kind;
    bubble.className = "bubble";
    bubble.textContent = text;
    box.appendChild(bubble);

    if (extra) box.appendChild(extra);

    chatLog.appendChild(box);
    chatLog.scrollTop = chatLog.scrollHeight;
}

// the three quick buttons
function makeButtons() {
    const box = document.createElement("div");
    box.className = "actions";

    const items = [
        { icon: "💬", label: "Start Bargaining", onClick: startBargaining },
        { icon: "🏷️", label: "View Clearance Deals", onClick: showClearanceDeals },
        { icon: "❓", label: "How It Works?", onClick: explain }
    ];

    items.forEach(function (item) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "action-btn";
        button.textContent = item.icon + " " + item.label;
        button.addEventListener("click", item.onClick);
        box.appendChild(button);
    });

    return box;
}

function welcome() {
    const hello = currentUser.guest ? "Hi!" : "Hi " + currentUser.name + "!";

    addMessage("assistant",
        hello + " I'm your AI shopping assistant. I can help you bargain for " +
        "better prices and find the best deals. What would you like to do today?",
        makeButtons());
}

function startBargaining() {
    addMessage("user", "Start Bargaining");

    const available = pickFeatured();

    if (available.length === 0) {
        addMessage("assistant", "There are no products available right now.");
        return;
    }

    const chips = document.createElement("div");
    chips.className = "chips";

    available.forEach(function (product) {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "chip";
        chip.textContent = product.name + " · " + formatPrice(product.price);
        chip.addEventListener("click", function () {
            openBargainPage(product);
        });
        chips.appendChild(chip);
    });

    addMessage("assistant",
        "Great! Pick a product and I'll open the bargaining page for you. " +
        "You can also press Bargain Now on any product.",
        chips);
}

function showClearanceDeals() {
    addMessage("user", "View Clearance Deals");

    const deals = products.filter(function (p) { return isClearance(p) && p.stock > 0; });

    changeView("clearance");
    setActiveNav("clearance");
    scrollToElement($("products"));

    if (deals.length === 0) {
        addMessage("assistant", "There are no clearance deals right now. Check back soon!");
    } else {
        addMessage("assistant", "Here are today's clearance deals (" + deals.length + "). Press Bargain Now on any of them.");
    }
}

function explain() {
    addMessage("user", "How It Works?");
    addMessage("assistant",
        "1. Pick a product and choose how many you want.\n" +
        "2. Tell me your price, in any language.\n" +
        "3. I accept, counter or decline, for up to 3 rounds.\n" +
        "4. When we agree, the deal is locked in.",
        makeButtons());
}

$("chatForm").addEventListener("submit", function (event) {
    event.preventDefault();

    const text = messageInput.value.trim();
    if (!text) return;

    messageInput.value = "";
    addMessage("user", text);
    addMessage("assistant", "Pick a product first and I'll open the bargaining page for you.", makeButtons());
});


// ---------- start ----------

// links like index.html?view=clearance
const wantedView = new URLSearchParams(window.location.search).get("view");

if (wantedView === "all" || wantedView === "clearance") {
    view = wantedView;
    setActiveNav(wantedView === "all" ? "products" : "clearance");
}

initNavbar().then(welcome);   // the greeting needs to know who is logged in
loadProducts();