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

Then start the shop: `cd ../ecommerce-platform-frontend && npm install && npm run dev`

Demo coupon: `WELCOME10`

## Docker

```bash
copy .env.example .env
docker compose up --build
```

## Production env

```
CORS_ALLOWED_ORIGINS=https://your-shop.example.com
CSRF_TRUSTED_ORIGINS=https://your-shop.example.com
ALLOWED_HOSTS=api.your-shop.example.com
PAYMENT_SUCCESS_URL=https://your-shop.example.com/checkout/success
SECRET_KEY=<40+ random chars>
DJANGO_SETTINGS_MODULE=config.settings.production
DATABASE_URL=postgres://...
```
