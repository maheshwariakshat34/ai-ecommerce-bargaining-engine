# 🛍️ AI E-Commerce Bargaining & Dynamic Clearance Engine

An AI-powered Flask e-commerce backend where customers can **bargain in natural language** (Hindi, English, Hinglish) and prices **adjust automatically** based on inventory pressure.

> **Key design rule:** The LLM never decides a price. A deterministic rule engine makes every pricing decision. Groq AI is only used to *understand* what the customer wrote and to *word* the seller's reply.

---

## ✨ Features

### 🏷️ Dynamic Clearance Engine
Scores every product with a **pressure score (0–1)** from five signals:
- **Days of cover** (stock ÷ daily sales)
- **Inventory age**
- **Demand level** (HIGH / MEDIUM / LOW)
- **Sales trend** (last 7 days vs 30-day average)
- **Expiry urgency**

Rules:
- No discount while the product is healthy (pressure < 0.20)
- Discount grows with pressure, capped at **50%**
- Products within 7 days of expiry → forced high-pressure clearance
- Price never goes below **cost price** and never above **base price**
- Clearance levels: `NORMAL` → `MEDIUM` → `HIGH` → `URGENT` → `EXTREME`

### 📦 Bulk Discount
| Quantity | Discount |
|----------|----------|
| 3+ | 3% |
| 5+ | 5% |
| 10+ | 8% |

Applied on top of clearance price, always protected by cost-price floor.

### 🤝 AI Bargaining (3 Rounds)
- Customer makes offers via **natural language chat** or direct number
- Seller can **ACCEPT**, **COUNTER** or **REJECT**
- Offers ≥ 80% of target price get a counter-offer; lower offers are rejected
- A counter-offer is **binding** — if customer accepts it later, it is honoured
- Counters never go *up* compared with an earlier counter
- Round 3 is final: offer at/above floor is accepted, else session closes
- On acceptance: stock reduces, sale is recorded, cart item auto-added

### 🤖 AI Chat Layer (Groq)
`POST /api/bargaining/chat` takes a natural message like *"bhai 1700 mein de do"* or *"ok deal"* and:
1. **Groq** extracts intent (`OFFER`, `ACCEPT_COUNTER`, `QUESTION`, `OTHER`) + amount + language
2. **Rule engine** decides (ACCEPT / COUNTER / REJECT)
3. **Groq** writes a friendly reply in the customer's own language

**Safety measures:**
- Groq never sees cost price, floor price or target price
- Any AI reply containing an amount not provided is discarded → template fallback
- 12-second timeout; regex fallback keeps chat working if Groq is unavailable
- Customer messages are treated as data, not instructions

### 🛒 Cart & Orders
- Confirmed bargain deals auto-add to cart
- Customer can also add regular-priced items
- Place order from cart → order history page

### 📊 Seller Dashboard
- Stat cards: Confirmed Deals, Active Negotiations, Total Orders, Revenue
- Full deals table: buyer name/email, product, original price, deal price, savings, rounds used
- Full orders table: buyer, items, total, time placed
- Auto-refreshes every 30 seconds
- Admin-only access

### 🔐 Auth System
- User registration & login (session cookies)
- Admin vs Customer roles
- Login required to start bargaining

---

## 🗂️ Project Structure

```
ai-ecommerce-bargaining-engine/
├── backend/
│   ├── app.py                    # Flask app, blueprint registration, page routes
│   ├── seed.py                   # Sample product data
│   ├── config.py                 # App configuration
│   ├── models/
│   │   ├── product.py            # Product + db instance
│   │   ├── bargaining_session.py # Bargaining session state
│   │   ├── offer.py              # Offer history per session
│   │   ├── user.py               # User (customer / admin)
│   │   ├── cart.py               # Cart items
│   │   └── order.py              # Orders & order items
│   ├── routes/
│   │   ├── auth_routes.py        # /api/auth — register, login, logout, me
│   │   ├── product_routes.py     # /api/products — CRUD
│   │   ├── offer_routes.py       # /api/bargaining — start, offer, chat, confirm
│   │   ├── clearance_routes.py   # /api/clearance — clearance data (admin)
│   │   ├── cart_routes.py        # /api/cart — cart & place order
│   │   └── seller_routes.py      # /api/seller — dashboard, deals, orders
│   └── services/
│       ├── clearance_engine.py   # Pressure score & clearance price
│       ├── pricing_engine.py     # Bulk discount & cost protection
│       ├── bargaining_service.py # ACCEPT / COUNTER / REJECT logic
│       ├── ai_negotiator.py      # Groq: understand message, write reply
│       └── security.py           # Auth decorators, session helpers
└── frontend/
    ├── index.html / style.css / script.js    # Product catalog
    ├── bargain.html / bargain.css / bargain.js # Bargaining chat UI
    ├── login.html / login.css / login.js      # Auth pages
    ├── admin.html / admin.css                 # Admin product panel
    ├── orders.html / orders.css / orders.js   # Customer orders
    ├── seller.html / seller.css / seller.js   # Seller dashboard
    └── common.js                              # Shared navbar, cart badge
```

---

## 🚀 Setup

### 1. Clone & Install
```bash
git clone <repo-url>
cd ai-ecommerce-bargaining-engine

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac / Linux

pip install -r requirements.txt
```

### 2. Create `.env` in project root
```env
GROQ_API_KEY=gsk_your_groq_key_here
GROQ_MODEL=qwen/qwen3.8-27b
ADMIN_KEY=a-long-random-secret
```

Get a free Groq API key at **https://console.groq.com** → API Keys.

> ⚠️ Never commit `.env` — it is already in `.gitignore`.

### 3. Seed the database
```bash
python -m backend.seed
```

### 4. Run
```bash
python -m flask --app backend.app run --debug
```

Server starts at → **http://127.0.0.1:5000**

---

## 🗺️ Pages

| URL | Page |
|-----|------|
| `/` | Product Catalog |
| `/bargain?product=<id>` | AI Bargaining Chat |
| `/login` | Login / Register |
| `/admin` | Admin Product Panel |
| `/orders` | Customer Order History |
| `/seller` | Seller Dashboard |

---

## 📡 API Reference

> Admin requests require login as `role=admin` **or** the header `X-Admin-Key: <ADMIN_KEY>`.

### Customer Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register `{ name, email, password }` |
| POST | `/api/auth/login` | Login `{ email, password }` |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Current user info |
| GET | `/api/products` | Product list (public fields only) |
| POST | `/api/bargaining/start` | Start session `{ product_id, quantity }` |
| POST | `/api/bargaining/offer` | Numeric offer `{ session_id, customer_offer }` |
| POST | `/api/bargaining/chat` | Chat message `{ session_id, message }` |
| POST | `/api/bargaining/confirm` | Confirm a deal `{ session_id }` |
| GET | `/api/bargaining/session/<id>` | Session status & round history |
| GET | `/api/cart` | View cart |
| POST | `/api/cart/add` | Add item to cart |
| DELETE | `/api/cart/<id>` | Remove cart item |
| POST | `/api/cart/place-order` | Place order from cart |
| GET | `/api/orders` | Customer order history |

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products` | Full product data (cost, minimum price, sales) |
| POST | `/api/products` | Add product |
| PUT | `/api/products/<id>` | Update product |
| DELETE | `/api/products/<id>` | Delete product |
| GET | `/api/clearance/<id>` | Clearance price, level, pressure scores |
| GET | `/api/seller/dashboard` | Summary stats |
| GET | `/api/seller/deals` | All confirmed bargaining deals |
| GET | `/api/seller/orders` | All placed orders |

---

## 🧠 How a Price is Decided

```
Customer offer
    │
    ▼
clearance_engine  →  clearance price (based on stock pressure)
    │
    ▼
pricing_engine    →  bulk discount + cost-price floor
    │
    ▼
bargaining_service →  ACCEPT / COUNTER / REJECT
    │
    ▼
ai_negotiator     →  friendly reply in customer's language
                      (Groq only words the reply — no price decisions)
```

- **Floor price** = total cost price (seller never loses money)
- **Target price** = discounted price the seller is happy to accept
- **Counter price** = midpoint between target and customer's offer

---

## 🔒 Security Notes

- Keep `.env` out of git. If a key was ever committed, regenerate it immediately.
- Customer API responses never include cost, floor, target or clearance internals.
- Session ownership is enforced — users cannot submit offers on another user's session.
- The `ADMIN_KEY` is a simple shared secret, suitable for demos. Use proper OAuth for production.

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask, Flask-SQLAlchemy |
| Database | SQLite (via SQLAlchemy ORM) |
| AI | Groq API (`qwen/qwen3.8-27b`) |
| Auth | Flask sessions (signed cookies) |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Config | python-dotenv |

---

## 🛣️ Known Limitations / Future Work

- Active bargaining sessions never expire (session cleanup not implemented)
- `seasonal_factor` is stored but not yet used in clearance scoring
- Money values use `Float`; use `Numeric` for real payment systems
- Payment integration (Razorpay / Stripe) not yet implemented
- Product images are served from local `/images/` folder (no upload UI)
