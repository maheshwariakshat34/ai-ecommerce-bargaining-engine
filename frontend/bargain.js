const chatLog = $("chatLog");
const messageInput = $("messageInput");
const sendBtn = $("sendBtn");

// everything we know about the current bargaining
let product = null;
let quantity = 1;
let sessionId = null;
let maxRounds = 3;
let lastCounter = null;   // seller's last counter price (total)
let confirming = false;   // true when the price is agreed and only your confirmation is missing
let finished = false;
let busy = false;
let rounds = [];          // offers and replies shown on the left


// ---------- chat messages ----------

// scrolls to the newest message; repeats once the browser has laid out
// cards and images, otherwise the bottom of a tall message stays hidden
function scrollChatToEnd() {
    chatLog.scrollTop = chatLog.scrollHeight;
    requestAnimationFrame(function () {
        chatLog.scrollTop = chatLog.scrollHeight;
    });
    setTimeout(function () {
        chatLog.scrollTop = chatLog.scrollHeight;
    }, 150);
}

// text can be empty when the message is only a card
function addMessage(kind, text, extra) {
    const box = document.createElement("div");

    box.className = "msg " + kind;

    if (text) {
        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.textContent = text;   // textContent so reply text can never run as html
        box.appendChild(bubble);
    }

    if (extra) box.appendChild(extra);

    chatLog.appendChild(box);
    scrollChatToEnd();
    return box;
}

function updateInput() {
    const active = sessionId !== null && !finished;

    messageInput.disabled = !active || busy;
    sendBtn.disabled = !active || busy;
    $("acceptBtn").disabled = busy;

    if (sessionId === null) {
        messageInput.placeholder = "Start bargaining first...";
    } else if (finished) {
        messageInput.placeholder = "This negotiation has ended";
    } else {
        messageInput.placeholder = "Type your offer, e.g. 1700 mein de do";
    }
}

function showRoundPill() {
    $("roundPill").textContent = rounds.length + "/" + maxRounds + " rounds";
    $("roundPill").hidden = false;
}

function showAcceptBar() {
    if (lastCounter === null || finished) {
        $("acceptBar").hidden = true;
        return;
    }

    let text = (confirming ? "Confirm the deal at " : "Seller's price: ") + formatPrice(lastCounter);
    if (quantity > 1) {
        text += " total (" + formatPrice(lastCounter / quantity) + " each)";
    }

    $("acceptText").textContent = text;
    $("acceptBtn").textContent = confirming ? "Confirm deal" : "Accept this price";
    $("acceptBar").hidden = false;
}


// ---------- left side: product ----------

function showProduct() {
    const badge = badgeFor(product);
    const started = sessionId !== null;

    let html = '<div class="product-image b-image">';
    if (badge) {
        html += '<span class="badge ' + badge.color + '">' + badge.text + "</span>";
    }
    html += thumbHtml(product) + "</div>";

    html += '<p class="b-category">' + escapeHtml(product.category || "") + "</p>";
    html += '<h1 class="b-name">' + escapeHtml(product.name) + "</h1>";

    html += '<div class="price-row">';
    if (isClearance(product)) {
        html += '<span class="old-price">' + formatPrice(product.base_price) + "</span>";
    }
    html += '<span class="current-price">' + formatPrice(product.price) + "</span>";
    html += '<span class="b-stock">per item</span></div>';
    html += '<p class="b-stock">' + product.stock + " in stock</p>";

    if (started) {
        html += '<div class="b-locked">' +
            "<span>Quantity: <strong>" + quantity + "</strong></span>" +
            "<span>List total: <strong>" + formatPrice(product.price * quantity) + "</strong></span>" +
            "</div>";
    } else {
        html += '<div class="b-setup">' +
            '<label for="qtyInput">How many do you want?</label>' +
            '<div class="qty-row">' +
            '<button class="qty-btn" id="qtyMinus" type="button">−</button>' +
            '<input type="number" id="qtyInput" min="1" max="' + product.stock + '" value="1">' +
            '<button class="qty-btn" id="qtyPlus" type="button">+</button>' +
            "</div>" +
            '<p class="b-error-text" id="setupError"></p>' +
            '<button class="b-start" id="startBtn" type="button">Start bargaining →</button>' +
            "</div>";
    }

    $("productCard").innerHTML = html;

    if (!started) {
        $("qtyMinus").addEventListener("click", function () {
            const now = parseInt($("qtyInput").value, 10) || 1;
            $("qtyInput").value = Math.max(1, now - 1);
        });
        $("qtyPlus").addEventListener("click", function () {
            const now = parseInt($("qtyInput").value, 10) || 1;
            $("qtyInput").value = Math.min(product.stock, now + 1);
        });
        $("startBtn").addEventListener("click", startSession);
        $("qtyInput").addEventListener("keydown", function (event) {
            if (event.key === "Enter") startSession();
        });
    }
}

// the login ran out in the middle of bargaining
function loginExpired() {
    const link = document.createElement("a");
    link.href = loginUrl();
    link.textContent = "Log in again";
    addMessage("system", "Your login has expired.", link);
}

function showProblem(html) {
    $("productCard").innerHTML = '<p class="b-error">' + html + "</p>";
}


// ---------- left side: rounds ----------

function showRounds() {
    const list = $("roundsList");
    list.innerHTML = "";

    rounds.forEach(function (round, index) {
        const item = document.createElement("li");
        const title = document.createElement("strong");
        const offer = document.createElement("span");
        const result = document.createElement("span");

        item.className = "round-item";
        title.textContent = "Round " + (round.number || index + 1);

        offer.textContent = "Your offer: " + formatPrice(round.offer);
        if (quantity > 1) {
            offer.textContent += " (" + formatPrice(round.offer / quantity) + " each)";
        }

        if (round.decision === "COUNTER") {
            result.className = "decision counter";
            result.textContent = "Seller countered " + formatPrice(round.counter);
        } else if (round.decision === "CONFIRM") {
            result.className = "decision counter";
            result.textContent = "Seller agreed to " + formatPrice(round.counter) +
                " (waiting for your confirmation)";
        } else if (round.decision === "ACCEPT") {
            result.className = "decision accept";
            result.textContent = "Deal at " + formatPrice(round.final);
        } else {
            result.className = "decision reject";
            result.textContent = "Seller declined";
        }

        item.append(title, offer, result);
        list.appendChild(item);
    });
}


// ---------- end of the negotiation ----------

function makeLink(text) {
    const box = document.createElement("div");
    const link = document.createElement("a");

    box.className = "deal-actions";
    link.className = "btn-link";
    link.href = "index.html";
    link.textContent = text;
    box.appendChild(link);

    return box;
}

function dealDone(total) {
    finished = true;
    $("acceptBar").hidden = true;

    const listTotal = product.price * quantity;
    const saved = Math.round((listTotal - total) * 100) / 100;

    const card = document.createElement("div");
    card.className = "deal-card";

    const title = document.createElement("strong");
    title.textContent = "Deal done! 🎉";
    card.appendChild(title);

    const totalLine = document.createElement("span");
    totalLine.textContent = "Total: " + formatPrice(total);
    card.appendChild(totalLine);

    if (quantity > 1) {
        const each = document.createElement("span");
        each.textContent = formatPrice(total / quantity) + " each × " + quantity;
        card.appendChild(each);
    }

    if (saved > 0) {
        const savedLine = document.createElement("span");
        savedLine.textContent = "You saved " + formatPrice(saved) + " on the list price";
        card.appendChild(savedLine);
    }

    card.appendChild(makeLink("Continue shopping"));

    addMessage("assistant", "", card);
    updateInput();
}

function noDeal() {
    finished = true;
    $("acceptBar").hidden = true;

    addMessage("system", "The negotiation has ended without a deal.");
    addMessage("assistant", "You can try another product anytime.", makeLink("Back to products"));
    updateInput();
}

// handles the reply of /chat and /offer
function handleReply(data) {
    const text = data.reply || data.message;
    if (text) addMessage("assistant", text);

    if (data.decision) {
        // confirming a price updates the round that held it, it is not a new round
        const held = data.confirmed
            ? rounds.filter(function (r) { return r.number === data.round_number; })[0]
            : null;

        if (held) {
            held.decision = "ACCEPT";
            held.final = data.final_price;
        } else {
            rounds.push({
                number: data.round_number,
                offer: data.customer_offer,
                decision: data.decision,
                counter: data.counter_price,
                final: data.final_price
            });
        }

        showRounds();
        showRoundPill();
    }

    if (data.decision === "COUNTER" || data.decision === "CONFIRM") {
        lastCounter = data.counter_price;
        confirming = data.decision === "CONFIRM";
    }

    // the customer said "ok": the same price is shown again, waiting for the button
    if (data.awaiting_confirmation && data.pending_price !== null && data.pending_price !== undefined) {
        lastCounter = data.pending_price;
        confirming = true;
    }

    if (data.session_status === "ACCEPTED") {
        if (!finished) dealDone(data.final_price);
    } else if (data.session_status === "CLOSED") {
        if (!finished) noDeal();
    } else {
        showAcceptBar();
    }
}


// ---------- talking to the server ----------

async function startSession() {
    const wanted = parseInt($("qtyInput").value, 10);

    if (!Number.isInteger(wanted) || wanted < 1 || wanted > product.stock) {
        $("setupError").textContent = "Please choose a quantity between 1 and " + product.stock + ".";
        return;
    }

    $("startBtn").disabled = true;
    $("setupError").textContent = "";

    try {
        const result = await post("/api/bargaining/start", {
            product_id: product.id,
            quantity: wanted
        });

        if (result.status === 401) {
            window.location.assign(loginUrl());
            return;
        }

        if (!result.ok) {
            $("setupError").textContent = result.data.error || "Could not start bargaining. Please try again.";
            $("startBtn").disabled = false;
            return;
        }

        sessionId = result.data.session.id;
        quantity = wanted;
        maxRounds = result.data.session.max_rounds;

        // so a refresh opens the same bargaining again
        window.history.replaceState(null, "", "bargain.html?product=" + product.id + "&session=" + sessionId);

        showProduct();
        showRounds();
        showRoundPill();

        let hello = "Great choice! " + product.name + " is listed at " +
            formatPrice(product.price) + " per item. Type your offer and let's make a deal.";
        if (quantity > 1) {
            hello += " You are buying " + quantity + ", so the prices in my replies are for the whole order.";
        }

        addMessage("assistant", hello);
        updateInput();
        messageInput.focus();
    } catch (error) {
        $("setupError").textContent = "Could not reach the server. Please try again.";
        $("startBtn").disabled = false;
        setOnline(false);
    }
}

async function sendMessage(text) {
    busy = true;
    updateInput();
    addMessage("user", text);

    const typing = addMessage("assistant typing", "Typing…");

    try {
        const result = await post("/api/bargaining/chat", {
            session_id: sessionId,
            message: text
        });

        typing.remove();

        if (!result.ok) {
            if (result.status === 401) {
                loginExpired();
            } else if (result.status === 429) {
                addMessage("system", "You are sending messages too fast. Please wait a moment.");
            } else {
                addMessage("system", result.data.error || "Something went wrong. Please try again.");
            }
        } else {
            handleReply(result.data);
        }
    } catch (error) {
        typing.remove();
        addMessage("system", "Could not reach the server. Please try again.");
        setOnline(false);
    }

    busy = false;
    updateInput();
    if (!finished) messageInput.focus();
}

// pressing the button confirms the seller's last price.
// This is the ONLY place where a deal is made; chat messages never make one.
async function acceptCounter() {
    if (lastCounter === null || busy || finished) return;

    busy = true;
    updateInput();
    addMessage("user", (confirming ? "I confirm " : "I accept ") + formatPrice(lastCounter) + ".");

    try {
        const result = await post("/api/bargaining/confirm", {
            session_id: sessionId
        });

        if (result.status === 401) {
            loginExpired();
        } else if (!result.ok) {
            addMessage("system", result.data.error || "Could not confirm the deal. Please try again.");
        } else {
            const data = result.data;

            data.reply = "Deal! " + product.name + " is yours at " +
                formatPrice(data.final_price) + ". Thank you!";

            handleReply(data);
        }
    } catch (error) {
        addMessage("system", "Could not reach the server. Please try again.");
        setOnline(false);
    }

    busy = false;
    updateInput();
}

$("chatForm").addEventListener("submit", function (event) {
    event.preventDefault();

    const text = messageInput.value.trim();
    if (!text || busy || finished || sessionId === null) return;

    messageInput.value = "";
    sendMessage(text);
});

$("acceptBtn").addEventListener("click", acceptCounter);


// ---------- opening an old session ----------

async function openOldSession(id, allProducts) {
    let response;

    try {
        response = await fetch("/api/bargaining/session/" + id);
    } catch (error) {
        setOnline(false);
        showProblem('Could not reach the server. <a href="index.html">Back to products</a>');
        return;
    }

    if (!response.ok) {
        showProblem('This bargaining session was not found. <a href="index.html">Back to products</a>');
        return;
    }

    const data = await response.json();
    const session = data.session;

    product = allProducts.find(function (p) { return p.id === session.product_id; });

    // product may be missing from the list (for example it expired), use what the session gave us
    if (!product) {
        const info = data.product || {};
        product = {
            id: info.id,
            name: info.name || "Product",
            category: "",
            base_price: info.base_price,
            price: info.base_price,
            discount_percent: 0,
            stock: info.stock || 0
        };
    }

    sessionId = session.id;
    quantity = session.quantity;
    maxRounds = session.max_rounds;

    rounds = (data.bargaining_history || []).map(function (item) {
        return {
            number: item.round_number,
            offer: item.customer_offer,
            decision: item.seller_response,
            counter: item.counter_price,
            final: item.final_price
        };
    });

    // last counter price the seller gave
    rounds.forEach(function (round) {
        if (round.counter !== null) lastCounter = round.counter;
    });

    showProduct();
    showRounds();
    showRoundPill();

    if (session.status === "ACCEPTED") {
        dealDone(session.final_price);
    } else if (session.status === "CLOSED") {
        noDeal();
    } else {
        addMessage("assistant",
            "Welcome back! You have used " + rounds.length + " of " + maxRounds +
            " rounds. Type your next offer to continue.");
        showAcceptBar();
    }

    updateInput();
}


// ---------- start ----------

async function start() {
    await initNavbar();
    updateInput();

    const params = new URLSearchParams(window.location.search);
    const productId = parseInt(params.get("product"), 10);
    const oldSession = parseInt(params.get("session"), 10);

    // the shop asks for a login before bargaining
    if (loginRequired && currentUser.guest) {
        showProblem('Please <a href="' + loginUrl() + '">log in</a> to bargain. ' +
            '<a href="index.html">Back to products</a>');
        return;
    }

    let allProducts = [];

    try {
        const response = await fetch("/api/products");
        if (!response.ok) throw new Error("bad response");

        allProducts = await response.json();
        setOnline(true);
    } catch (error) {
        setOnline(false);
        showProblem('Could not load the product. Is the server running? <a href="index.html">Back to products</a>');
        return;
    }

    if (Number.isInteger(oldSession)) {
        await openOldSession(oldSession, allProducts);
        return;
    }

    product = allProducts.find(function (p) { return p.id === productId; });

    if (!product || product.stock <= 0) {
        showProblem('This product is not available. <a href="index.html">Choose another product</a>');
        return;
    }

    showProduct();
    addMessage("assistant",
        "Hi! Choose how many you want on the left and press Start bargaining. " +
        "Then tell me your price, in any language.");
}

start();