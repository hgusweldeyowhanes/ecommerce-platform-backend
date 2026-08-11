"""
Ecommerce Platform API
======================

Django REST backend: catalog, cart, orders, payments (Stripe + Chapa),
inventory, reviews, and notifications.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_catalog   # optional demo data
python manage.py createsuperuser
python manage.py runserver
```

API root: http://127.0.0.1:8000/api/v1/

## Main endpoints

| Area | Base path |
|------|-----------|
| Auth | `/api/v1/auth/` register, token, me |
| Products | `/api/v1/products/` list, detail, categories |
| Cart | `/api/v1/cart/` get, add/update/remove items |
| Orders | `/api/v1/orders/` checkout, history |
| Payments | `/api/v1/payments/` init, webhook |
| Reviews | `/api/v1/reviews/` product reviews |
| Inventory | `/api/v1/inventory/` stock (staff) |

## Settings

- `config.settings.development` (default)
- `config.settings.production`

## Docker

```bash
docker compose up --build
```

## Architecture notes

- Domain logic in `services.py` / read paths in `selectors.py`
- Split settings for env-specific config
- Payment gateways pluggable under `apps/payments/gateways/`
- Celery tasks for emails/stock when Redis is available
"""
