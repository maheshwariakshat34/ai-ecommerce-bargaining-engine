# AI Interactive Bargaining & Dynamic Clearance Engine

A Flask backend for an e-commerce store where:

- **Prices adjust automatically** based on inventory pressure (overstock, aging stock, slow sales, expiry), and
- **Customers can bargain in natural language** (English, Hindi or Hinglish) with an AI-powered seller.

The most important design rule: **the LLM never decides a price.** A deterministic rule engine makes every pricing decision. Gemini is only used to *understand* what the customer wrote and to *word* the seller's reply.

---

## Features

### Dynamic clearance engine
- Scores every product with a **pressure score (0 to 1)** from five signals:
  - **Days of cover** (stock ÷ daily sales), so stock is judged against sales speed
  - **Inventory age**
  - **Demand level** (HIGH / MEDIUM / LOW)
  - **Sales trend** (last 7 days vs 30-day average)
  - **Expiry urgency**
- No discount while the product is healthy (pressure below 0.20).
- Discount grows with pressure, capped at **50%**.
- Products within 7 days of expiry are forced into high-pressure clearance.
- Price never goes below **cost price** and never above **base price**.
- Clearance levels: `NORMAL`, `MEDIUM`, `HIGH`, `URGENT`, `EXTREME`.

### Bulk discount
| Quantity | Discount |
|---|---|
| 3+ | 3% |
| 5+ | 5% |
| 10+ | 8% |

Applied on top of the clearance price and always protected by the cost-price floor.

### Bargaining (3 rounds)
- The customer makes offers (as a number or as a chat message).
- The seller can **ACCEPT**, **COUNTER** or **REJECT**.
- Offers of at least 80% of the target price get a counter-offer; lower offers are rejected.
- A seller counter-offer is **binding**: if the customer later offers that amount, it is accepted.
- Counters never go up compared with an earlier counter.
- Round 3 is final: an offer at or above the floor is accepted, anything below is rejected and the session closes.
- On acceptance, **stock is reduced** and the sale is recorded, so the clearance engine keeps learning.

### AI chat layer (Gemini)
`POST /api/bargaining/chat` takes a normal message such as *"bhai 1700 mein de do"* or *"ok deal"* and:
1. Gemini extracts the intent (`OFFER`, `ACCEPT_COUNTER`, `QUESTION`, `OTHER`) and the amount.
2. The rule engine decides.
3. Gemini writes a friendly reply in the **customer's own language**.

Safety measures:
- Gemini never sees cost price, floor price or target price.
- Any reply containing an amount that was not provided is discarded and replaced with a template reply.
- If Gemini is unavailable, a regex fallback and template replies keep the chat working.
- Customer messages are treated as data, not instructions.

### Seller protection
- Customers never see cost price, minimum price, floor, target price or internal clearance data.
- Product create / update / delete and clearance data require an **admin key**.

---

## Tech stack
- Python 3.10+
- Flask, Flask-SQLAlchemy (SQLite)
- Google Gemini (`google-genai`)
- `python-dotenv`

---

## Project structure

```
backend/
├── app.py                      # Flask app, blueprint registration
├── seed.py                     # Sample products
├── models/
│   ├── product.py              # Product + db instance
│   ├── bargaining_session.py   # Bargaining session
│   └── offer.py                # Offer history (unique per session + round)
├── routes/
│   ├── product_routes.py       # Product CRUD (admin protected for writes)
│   ├── clearance_routes.py     # Clearance data (admin only)
│   └── offer_routes.py         # Start, offer, chat, session history
└── services/
    ├── clearance_engine.py     # Pressure score and clearance price
    ├── pricing_engine.py       # Bulk discount and cost protection
    ├── bargaining_service.py   # ACCEPT / COUNTER / REJECT logic
    ├── ai_negotiator.py        # Gemini: understand message, write reply
    └── security.py             # Admin key check
```

---

## Setup

### 1. Install
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac / Linux
pip install -r requirements.txt
```

`requirements.txt` must include `flask`, `flask-sqlalchemy`, `google-genai` and `python-dotenv`.

### 2. Create a `.env` file in the project root
```
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=your-gemini-model-name
ADMIN_KEY=a-long-random-secret
```
Get a Gemini key at https://aistudio.google.com/apikey. **Never commit `.env`**; make sure `.gitignore` contains `.env` and `*.db`.

### 3. Create the database and sample data
```bash
python -m backend.seed
```

### 4. Run
```bash
python -m backend.app
```
The server starts at `http://127.0.0.1:5000`.

---

## API reference

Admin requests must send the header `X-Admin-Key: <ADMIN_KEY>`.

### Customer endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/products` | Product list (id, name, category, base_price, stock only) |
| POST | `/api/bargaining/start` | Start a session `{ "product_id": 1, "quantity": 1 }` |
| POST | `/api/bargaining/offer` | Submit a numeric offer `{ "session_id": 1, "customer_offer": 1700 }` (**total** price) |
| POST | `/api/bargaining/chat` | Chat message `{ "session_id": 1, "message": "1700 mein de do" }` |
| GET | `/api/bargaining/session/<id>` | Session status and round history |

### Admin endpoints (`X-Admin-Key` required)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/products` | Full product data including cost, minimum price, sales |
| POST | `/api/products` | Add a product |
| PUT | `/api/products/<id>` | Update a product |
| DELETE | `/api/products/<id>` | Delete a product |
| GET | `/api/clearance/<id>` | Clearance price, level, pressure scores, days of cover, reasons |
| POST | `/api/bargaining/offer` | Response additionally includes the `pricing` breakdown (target, floor, cost) |
| GET | `/api/bargaining/session/<id>` | Product block additionally includes cost and minimum price |

Product validation: `cost_price <= minimum_price <= base_price`, non-negative stock and sales, `demand_level` one of `LOW`, `MEDIUM`, `HIGH`.

---

## Example flow

```http
POST /api/bargaining/start
{ "product_id": 1, "quantity": 1 }

POST /api/bargaining/chat
{ "session_id": 1, "message": "bhai 1700 mein de do" }
```
```json
{
  "decision": "COUNTER",
  "counter_price": 1850.0,
  "reply": "Namaste! ₹1700 thoda kam hai, lekin main ₹1850 mein de sakta hoon.",
  "session_status": "ACTIVE",
  "round_number": 1
}
```
```http
POST /api/bargaining/chat
{ "session_id": 1, "message": "ok deal" }
```
```json
{
  "decision": "ACCEPT",
  "final_price": 1850.0,
  "session_status": "ACCEPTED"
}
```

---

## How a price is decided

```
Product data -> clearance_engine -> clearance price
             -> pricing_engine   -> bulk discount, cost protection
             -> bargaining_service -> ACCEPT / COUNTER / REJECT
             -> ai_negotiator    -> friendly reply (words only, no prices decided)
```

- **Floor price:** the total minimum price in normal conditions; the total **cost price** when clearance pushes the price below the normal minimum.
- **Target price:** the higher of the discounted bulk price and the floor. An offer at or above it is accepted **at the target price**, never above it.

---

## Security notes
- Keep `.env` out of git. If a key was ever committed, regenerate it.
- Customer responses never include cost, floor, target or internal clearance data.
- The admin key is a simple shared secret, suitable for a demo or project. Use proper authentication for production.
- Customer offers are **total** prices for the whole quantity. In chat, an amount is treated as per-unit unless the customer says "total".

---

## Known limitations
- Active bargaining sessions never expire.
- `seasonal_factor` is stored but not yet used in clearance scoring.
- Money values use `Float`; use `Numeric` for real payments.
- Accepting a deal reduces stock but does not create an order or payment.

---

## Roadmap
- Seller dashboard APIs (summary, clearance overview, sessions and profit)
- Customer chat frontend and seller dashboard UI
- Session expiry
- Use `seasonal_factor` in clearance scoring
- Orders and payments