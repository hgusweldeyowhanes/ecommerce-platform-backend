# Ecommerce API (Django REST)

Backend for **Adera**. Pair with `ecommerce-platform-frontend`.

## Local run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_catalog
python manage.py runserver
```

Use the project venv (`.venv\Scripts\activate`). Plain `python` on this machine is system 3.9 and is missing packages such as Celery. `manage.py` will switch to `.venv` automatically if it exists.

- API: http://127.0.0.1:8000/api/v1/
- Health: http://127.0.0.1:8000/health/live/
- Admin: http://127.0.0.1:8000/admin/
- Wishlist (auth): http://127.0.0.1:8000/api/v1/wishlist/

Then start the shop: `cd ../ecommerce-platform-frontend && npm install && npm run dev`

Demo coupon: `WELCOME10`

## Docker (local)

```bash
copy .env.example .env
docker compose up --build
```

## Deploy (production)

1. Copy `.env.production.example` to `.env`
2. Set `SECRET_KEY`, `POSTGRES_PASSWORD`, `ALLOWED_HOSTS`, CORS/CSRF origins, and `CHAPA_SECRET_KEY`
3. Create a superuser after first boot: `docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser`

```bash
copy .env.production.example .env
docker compose -f docker-compose.prod.yml up --build -d
```

The API is on port 80 (`/api/v1/`, `/media/`, `/health/live/`). Point the shop's `API_UPSTREAM` or `VITE_API_URL` at this host.

Put HTTPS in front (Caddy, nginx, or your host), then set `SECURE_SSL_REDIRECT=True` and `PAYMENT_SUCCESS_URL` to `https://...`.
