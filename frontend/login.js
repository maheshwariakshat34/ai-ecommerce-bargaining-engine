const params = new URLSearchParams(window.location.search);

let role = params.get("as") === "seller" ? "admin" : "user";
let mode = "login";
let busy = false;

function safeNext(raw) {
    if (typeof raw === "string" && /^[A-Za-z0-9_-]+\.html(\?[A-Za-z0-9_=&%.-]*)?$/.test(raw)) {
        return raw;
    }
    return null;
}

// where to go after login
function landingFor(user, next) {
    const target = safeNext(next);
    const sellerPage = target && /^admin\.html/.test(target);

    if (target && (user.role === "admin" || !sellerPage)) return target;
    return user.role === "admin" ? "admin.html" : "index.html";
}

function showError(message) {
    $("authError").textContent = message;
}

function render() {
    const seller = role === "admin";
    const signup = mode === "signup" && !seller;

    document.querySelectorAll(".auth-tab").forEach(function (tab) {
        tab.classList.toggle("on", tab.dataset.role === role);
    });

    $("nameRow").hidden = !signup;
    $("switchRow").hidden = seller;

    $("authTitle").textContent = seller ? "Seller login" : signup ? "Create your account" : "Welcome back";
    $("authSub").textContent = seller
        ? "Log in to manage products, prices and clearance."
        : signup ? "Sign up to start bargaining for better prices."
                 : "Log in to bargain and get the best price.";

    $("authSubmit").textContent = signup ? "Create account" : "Log in";
    $("passwordInput").autocomplete = signup ? "new-password" : "current-password";
    $("switchText").textContent = signup ? "Already have an account? " : "New here? ";
    $("switchBtn").textContent = signup ? "Log in" : "Create an account";
    showError("");
}

document.querySelectorAll(".auth-tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
        role = tab.dataset.role;
        mode = "login";
        render();
    });
});

$("switchBtn").addEventListener("click", function () {
    mode = mode === "login" ? "signup" : "login";
    render();
});

$("showPw").addEventListener("click", function () {
    const hidden = $("passwordInput").type === "password";
    $("passwordInput").type = hidden ? "text" : "password";
    $("showPw").textContent = hidden ? "Hide" : "Show";
});

$("authForm").addEventListener("submit", async function (event) {
    event.preventDefault();
    if (busy) return;

    const signup = mode === "signup" && role === "user";
    const name = $("nameInput").value.trim();
    const email = $("emailInput").value.trim();
    const password = $("passwordInput").value;

    // quick checks here, the server checks everything again
    if (signup && name.length < 2) return showError("Please enter your name.");
    if (!email.includes("@")) return showError("Please enter a valid email address.");
    if (!password) return showError("Please enter your password.");
    if (signup && password.length < 8) return showError("Password must be at least 8 characters.");

    busy = true;
    $("authSubmit").disabled = true;
    showError("");

    try {
        const result = signup
            ? await post("/api/auth/register", { name: name, email: email, password: password })
            : await post("/api/auth/login", { email: email, password: password, role: role });

        if (!result.ok) {
            showError(result.data.error || "Something went wrong. Please try again.");
        } else {
            showToast("Welcome, " + result.data.user.name + "!");
            window.location.assign(landingFor(result.data.user, params.get("next")));
            return;   // the button stays disabled while the page changes
        }
    } catch (error) {
        showError("Could not reach the server. Please try again.");
    }

    busy = false;
    $("authSubmit").disabled = false;
});

async function start() {
    render();
    await initNavbar();

    if (currentUser.guest) return;

    // already logged in: go on, unless a customer came here to use the seller login
    if (role === "admin" && currentUser.role !== "admin") {
        showError("You are logged in as a customer. Log out first to use the seller login.");
        return;
    }

    window.location.replace(landingFor({ role: currentUser.role }, params.get("next")));
}

start();
