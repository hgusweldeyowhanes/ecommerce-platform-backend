# Ecommerce Platform Backend — Project Documentation

> **Status:** This document matches the *implemented* codebase in `ecomerce-platform/`  
> (not a generic template). Last aligned with the service-layer Django REST API, base URL **`/api/v1/`**.

---

## Table of contents

1. [Overview](#1-overview)
2. [What is implemented vs roadmap](#2-what-is-implemented-vs-roadmap)
3. [Architecture](#3-architecture)
4. [Project structure](#4-project-structure)
5. [Configuration](#5-configuration)
6. [Applications](#6-applications)
7. [API reference](#7-api-reference)
8. [Domain flows](#8-domain-flows)
9. [Data model](#9-data-model)
10. [Auth](#10-auth)
11. [Payments](#11-payments)
12. [Run & Docker](#12-run--docker)
13. [Testing](#13-testing)
14. [Deployment notes](#14-deployment-notes)

---

## 1. Overview

Django REST API for catalog, cart, checkout, payments (Stripe / Chapa / mock), inventory reservation, reviews, and email-style notifications.

### Stack (as installed)

| Layer | Choice |
|-------|--------|
| Framework | Django 4.2.x |
| API | Django REST Framework + SimpleJWT |
| Filters | django-filter |
| DB | **SQLite by default**; Postgres via `DATABASE_URL` |
| Cache / queue | Redis + Celery (eager mode on by default in dev) |
| Payments | Stripe Checkout Session, Chapa initialize, **mock** complete URL |
| Containers | Docker Compose: `web`, `worker`, `db`, `redis` |

### Tech conventions in code

- **Settings:** `config.settings.development` (default in `manage.py`) / `production`
- **Apps:** `apps.<name>` packages under `apps/`
- **Business logic:** `services.py`
- **Read queries:** `selectors.py` (where present)
- **Shared helpers:** `common/`
- **Errors:** `common.exceptions.ServiceError` → HTTP 400 with `{detail, code}` from views

---

## 2. What is implemented vs roadmap

Use this table so docs and code stay honest.

| Feature | Implemented | Notes |
|---------|-------------|--------|
| JWT register / token / refresh / me | Yes | Username login via SimpleJWT (`token/`) |
| Address book CRUD | Yes | `/api/v1/auth/addresses/` |
| Categories + products CRUD | Yes | Staff write; public read |
| Product search / price / category filter | Yes | Query params on products list |
| Inventory quantity + reserved | Yes | Separate app, not a `stock` field on Product |
| Stock reserve / commit / release | Yes | Checkout reserves; pay commits |
| Guest + auth cart | Yes | Session key or user; merge guest→user |
| Checkout + order numbers | Yes | `POST /orders/checkout/` |
| Cancel pending order | Yes | `POST .../{order_number}/cancel/` |
| Payments mock / Stripe / Chapa | Yes | Keys empty → mock checkout URL |
| Stripe / Chapa webhooks (minimal) | Yes | Stubs under `/payments/webhooks/` |
| Reviews 1–5 stars | Yes | Unique `(product, user)` |
| Order placement email notification | Yes | Celery task + console email backend |
| Email verification / forgot password | **No** | Not in routes or models |
| Product multi-image / attributes models | **Partial** | `attributes` JSON + single `image` only |
| Discounts / coupons | **No** | |
| Shipment tracking model | **No** | Status only on Order |
| Refunds API | **No** | Status constant exists |
| In-app notification REST API | **No** | Model + email send only |
| Health path `/health/` | **No** | Use `GET /api/v1/` as discovery |
| Real-time websockets | **No** | |

---

## 3. Architecture

```
Client
  → Django URLconf (config/urls.py)
    → DRF views (apps/*/views.py)
      → serializers (validate I/O)
        → services.py  (business rules, transactions)
          → models / inventory / gateways
        → selectors.py (optional read helpers)
```

**Checkout / payment sketch**

```
Cart items
  → create_order_from_cart  (reserve stock, snapshot OrderItems, clear cart)
  → initiate_payment        (Payment row + gateway checkout_url)
  → complete_payment        (mock POST/GET or webhook)
  → mark_order_paid         (commit stock reservations)
```

---

## 4. Project structure

```
ecomerce-platform/
├── manage.py
├── requirements.txt
├── .env / .env.example
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── README.md
├── ECOMMERCE_BACKEND_DOCUMENTATION.md   ← this file
│
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py          # mounts /api/v1/*
│   ├── celery.py
│   ├── wsgi.py / asgi.py
│
├── apps/
│   ├── users/
│   ├── products/        # + management/commands/seed_catalog.py
│   ├── cart/
│   ├── orders/
│   ├── payments/        # gateways: mock, stripe.py, chapa.py
│   ├── inventory/
│   ├── reviews/
│   └── notifications/   # no public HTTP API yet
│
├── common/              # pagination, exceptions, permissions, constants, utils
├── tests/integration/
└── scripts/
    ├── seed_data.py     # calls seed_catalog
    └── wait_for_db.sh
```

---

## 5. Configuration

Copy `.env.example` → `.env`. Variables **actually read** by `config/settings/base.py`:

```env
DEBUG=True
SECRET_KEY=...
DJANGO_SETTINGS_MODULE=config.settings.development
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Empty → SQLite (db.sqlite3). Docker sets Postgres URL.
DATABASE_URL=

REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
# Dev default: CELERY_TASK_ALWAYS_EAGER=True (in development.py / base default)

STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
CHAPA_SECRET_KEY=
CHAPA_PUBLIC_KEY=
CHAPA_WEBHOOK_SECRET=
PAYMENT_SUCCESS_URL=http://localhost:5173/checkout/success
PAYMENT_CANCEL_URL=http://localhost:5173/checkout/cancel

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@ecommerce.local
DEFAULT_CURRENCY=USD
```

**Not used today:** separate `DB_ENGINE` / `DB_NAME` / `JWT_SECRET` / AWS S3 vars. JWT is configured via SimpleJWT settings (Django `SECRET_KEY` for signing).

---

## 6. Applications

### 6.1 Users (`apps.users`)

| Model | Fields (high level) |
|-------|---------------------|
| `User` | AbstractUser + `phone`, `is_vendor` |
| `Address` | `label`, line1/2, city, state, postal_code, country, `is_default` |

| Endpoint | Method | Auth |
|----------|--------|------|
| `/api/v1/auth/register/` | POST | Public |
| `/api/v1/auth/token/` | POST | Public (`username`, `password` → access/refresh) |
| `/api/v1/auth/token/refresh/` | POST | Public |
| `/api/v1/auth/me/` | GET, PATCH | JWT |
| `/api/v1/auth/addresses/` | CRUD | JWT |

### 6.2 Products (`apps.products`)

| Model | Notes |
|-------|--------|
| `Category` | `name`, `slug`, optional `parent` |
| `Product` | price, sku, image, `attributes` JSON, `is_featured` — **stock lives in inventory** |

| Endpoint | Notes |
|----------|--------|
| `/api/v1/products/` | List/create (create staff) |
| `/api/v1/products/{slug}/` | Detail by **slug** |
| `/api/v1/products/featured/` | Featured products |
| `/api/v1/products/categories/` | Categories CRUD |

Query filters: `search`, `category` (slug), `min_price`, `max_price`, `in_stock`, `is_featured`, ordering.

Seed: `python manage.py seed_catalog`

### 6.3 Inventory (`apps.inventory`)

| Model | Notes |
|-------|--------|
| `InventoryItem` | OneToOne Product: `quantity`, `reserved`, `low_stock_threshold` |
| `StockMovement` | in / out / reserve / release audit log |

| Endpoint | Auth |
|----------|------|
| `/api/v1/inventory/` | Staff |
| `/api/v1/inventory/adjust/` | Staff (`product_id`, `delta`) |
| `/api/v1/inventory/products/{id}/movements/` | Staff |

Services: `ensure_inventory`, `adjust_stock`, `reserve_stock`, `release_reservation`, `commit_reservation`.

### 6.4 Cart (`apps.cart`)

| Model | Notes |
|-------|--------|
| `Cart` | `user` **or** `session_key` |
| `CartItem` | product, quantity, snapshot `unit_price` |

| Endpoint | Auth |
|----------|------|
| `GET/DELETE /api/v1/cart/` | AllowAny (session or user) |
| `POST /api/v1/cart/items/` | `{product_id, quantity}` |
| `PATCH/DELETE /api/v1/cart/items/{id}/` | quantity update / remove |

No discounts endpoint.

### 6.5 Orders (`apps.orders`)

| Model | Notes |
|-------|--------|
| `Order` | `order_number`, status, totals, shipping fields, email |
| `OrderItem` | Line snapshot (name, sku, unit_price, qty) |

Statuses: `pending`, `paid`, `processing`, `shipped`, `delivered`, `cancelled`, `refunded`.

| Endpoint | Auth |
|----------|------|
| `POST /api/v1/orders/checkout/` | AllowAny (email required) |
| `GET /api/v1/orders/` | Auth (own orders; staff all) |
| `GET /api/v1/orders/{order_number}/` | Auth |
| `POST /api/v1/orders/{order_number}/cancel/` | Auth — pending only |

Checkout returns `{ order, payment }` in one call.

### 6.6 Payments (`apps.payments`)

| Model | Notes |
|-------|--------|
| `Payment` | `reference`, gateway, amount, status, `checkout_url`, `gateway_payment_id` |

Gateways: `mock`, `stripe`, `chapa` (`apps/payments/gateways/`).

| Endpoint | Notes |
|----------|--------|
| `GET /api/v1/payments/{reference}/` | Status |
| `GET|POST /api/v1/payments/mock/complete/{reference}/` | Marks success → pays order |
| `POST /api/v1/payments/webhooks/stripe/` | Minimal stub |
| `POST /api/v1/payments/webhooks/chapa/` | Minimal stub |

### 6.7 Reviews (`apps.reviews`)

| Endpoint | Notes |
|----------|--------|
| `/api/v1/reviews/` | CRUD; write requires auth; filter `?product=` |

Fields: `rating` 1–5, `title`, `body`, `is_approved` — **not** `verified_purchase` / helpful votes.

### 6.8 Notifications (`apps.notifications`)

- Model + `notify_order_placed` + Celery `send_notification_email`
- **No** REST routes registered for listing notifications

---

## 7. API reference

**Base URL:** `http://127.0.0.1:8000/api/v1/`

**Discovery:** `GET /api/v1/` → service name + endpoint map.

**Auth header:** `Authorization: Bearer <access>`

### Register

```http
POST /api/v1/auth/register/
Content-Type: application/json

{
  "username": "buyer1",
  "email": "buyer@example.com",
  "password": "StrongPass123!",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "phone": "+251900000000"
}
```

### Login (JWT)

```http
POST /api/v1/auth/token/

{
  "username": "buyer1",
  "password": "StrongPass123!"
}
```

Response: `{ "access": "...", "refresh": "..." }`

### List products

```http
GET /api/v1/products/?search=watch&min_price=10&max_price=200&page=1
```

Paginated: `{ count, next, previous, results }` (`common.pagination.StandardResultsPagination`).

### Cart → checkout → pay (happy path)

```http
POST /api/v1/cart/items/
{ "product_id": 1, "quantity": 2 }

POST /api/v1/orders/checkout/
{
  "email": "buyer@example.com",
  "shipping_name": "Ada Lovelace",
  "shipping_line1": "12 King St",
  "shipping_city": "Addis Ababa",
  "shipping_country": "ET",
  "shipping_fee": "5.00",
  "payment_gateway": "mock"
}
```

Response includes:

```json
{
  "order": { "order_number": "ORD-...", "status": "pending", "total": "..." },
  "payment": {
    "reference": "PAY-...",
    "gateway": "mock",
    "checkout_url": "/api/v1/payments/mock/complete/PAY-.../"
  }
}
```

```http
POST /api/v1/payments/mock/complete/PAY-.../
{ "success": true }
```

Order becomes `paid`; reserved stock is committed.

### Review

```http
POST /api/v1/reviews/
Authorization: Bearer ...

{
  "product": 1,
  "rating": 5,
  "title": "Great",
  "body": "Works as expected"
}
```

---

## 8. Domain flows

### Cart stock rules

- Add/update checks **available** stock = `quantity - reserved`
- Prices snapshot on `CartItem.unit_price` at add/update

### Order creation

1. Load cart (must be non-empty).
2. Create `Order` in `pending`.
3. For each line: `reserve_stock` then create `OrderItem`.
4. On failure mid-loop: release already reserved lines, delete order.
5. Clear cart, enqueue order notification.
6. Create `Payment` + return `checkout_url`.

### Payment success

`complete_payment(reference)` → `Payment.status = success` → `mark_order_paid` → `commit_reservation` per line.

### Cancel

`cancel_order` only for **pending** (releases reservation). Paid cancellation not supported via this API.

---

## 9. Data model (ORM reality)

### User

`username`, `email`, `password`, names, `phone`, `is_vendor`, standard Django flags.  
Login identifier for JWT: **username** (not email).

### Product

No `stock` column. Use:

```text
Product 1──1 InventoryItem(quantity, reserved)
```

Serializer exposes computed `stock_quantity` / `in_stock`.

### Order money

`subtotal` + `shipping_fee` + `tax` = `total` (`tax` default 0).

### Payment

`gateway` ∈ `mock|stripe|chapa`; status ∈ `pending|success|failed|refunded`.

---

## 10. Auth

- Packages: `rest_framework_simplejwt`
- Access lifetime: 12h; refresh: 7 days (see settings)
- Public: products (read), cart, checkout, payment mock/webhooks
- Staff: product write, inventory
- Owner/auth: orders list, reviews write, addresses

Permissions helpers: `common.permissions.IsAdminOrReadOnly`, `IsOwner`; users app `IsSelf`.

---

## 11. Payments

| Gateway | When keys set | When keys missing |
|---------|---------------|-------------------|
| **mock** | N/A | Primary local path |
| **stripe** | Stripe Checkout Session | Falls back to mock complete URL with warning in raw |
| **chapa** | Initialize API | Same fallback |

Env for real Chapa: `CHAPA_SECRET_KEY` (authorization bearer).  
Stripe: `STRIPE_SECRET_KEY` (+ optional webhook secret for future verify).

**Production note:** webhook handlers are minimal stubs—harden signature verification before live traffic.

---

## 12. Run & Docker

### Local (SQLite)

```bash
cd ecomerce-platform
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_catalog
python manage.py createsuperuser
python manage.py runserver
```

- Admin: http://127.0.0.1:8000/admin/  
- API: http://127.0.0.1:8000/api/v1/  

### Docker Compose

```bash
docker compose up --build
```

Services: Postgres, Redis, Gunicorn web (migrate + seed), Celery worker.  
Compose overrides `DATABASE_URL` to Postgres.

### Celery (non-eager)

Set `CELERY_TASK_ALWAYS_EAGER=False` and run:

```bash
celery -A config worker -l info
```

---

## 13. Testing

Present tests:

| Path | What |
|------|------|
| `tests/integration/test_checkout_flow.py` | Cart → checkout mock → pay |
| `apps/users/tests/test_auth.py` | Register |

```bash
python manage.py test tests.integration.test_checkout_flow apps.users.tests.test_auth -v2
# or
pytest
```

`tests/e2e/` is reserved (empty) for browser-level flows later.

---

## 14. Deployment notes

Production checklist tied to **this** project:

- [ ] `DJANGO_SETTINGS_MODULE=config.settings.production`
- [ ] `DEBUG=False`, strong `SECRET_KEY`
- [ ] `ALLOWED_HOSTS` / CORS origins for your frontend
- [ ] `DATABASE_URL` Postgres
- [ ] `CELERY_TASK_ALWAYS_EAGER=False` + Redis broker
- [ ] Real Stripe/Chapa keys + verify webhooks
- [ ] `python manage.py collectstatic`
- [ ] Gunicorn: `gunicorn config.wsgi:application --bind 0.0.0.0:8000`

```bash
gunicorn config.wsgi:application --workers 3 --bind 0.0.0.0:8000
```

---

## Quick comparison: old generic doc vs code

| Documented (old) | Actual project |
|------------------|----------------|
| `/api/users/`, `/api/products/` | **`/api/v1/auth/`**, **`/api/v1/products/`** |
| Email login | **Username** JWT |
| Product.`stock` | **InventoryItem.quantity** |
| Order create `POST /orders/` | **`POST /orders/checkout/`** |
| Payment POST body with card token | Checkout creates payment; **mock complete** URL |
| Forgot password / email verify | **Not implemented** |
| DB_* env vars | **`DATABASE_URL` or SQLite** |
| Notifications REST | **Email only** |
| Folder `ecommerce-backend` | Repo folder **`ecomerce-platform`** |

---

## Support

1. Prefer this file + `README.md` as the source of truth.  
2. For behavior, inspect `apps/*/services.py` and `config/urls.py`.  
3. Extend features (password reset, coupons, etc.) only after updating both code and this doc.

## External links

- [Django](https://docs.djangoproject.com/)
- [Django REST framework](https://www.django-rest-framework.org/)
- [SimpleJWT](https://django-rest-framework-simplejwt.readthedocs.io/)
- [Stripe Checkout](https://stripe.com/docs/payments/checkout)
- [Chapa](https://developer.chapa.co/)
- [Celery](https://docs.celeryq.dev/)
