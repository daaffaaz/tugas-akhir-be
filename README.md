# Backend (Django REST API)

Django 5 project with **Django REST Framework** and **PostgreSQL** (configured for **Supabase** via `DATABASE_URL`). Settings are split by environment; domain code lives under `apps/`.

## Project layout

| Path | Purpose |
|------|--------|
| `config/` | Django project package: URLs, WSGI/ASGI, and `settings/`. |
| `config/settings/base.py` | Shared settings (installed apps, middleware, DB from env, DRF). |
| `config/settings/local.py` | Development defaults (`DEBUG=True`, open `ALLOWED_HOSTS`). |
| `config/settings/production.py` | Production-only hardening (HTTPS-oriented flags). |
| `apps/` | Your Django apps. Each app is a package (e.g. `apps.users`). |
| `apps/users/` | Example app: models, DRF serializers/views, and `urls` mounted under `/api/`. |
| `requirements/` | Split dependencies: `base.txt`, `local.txt`, `production.txt` (adds `gunicorn`). |
| `manage.py` | CLI entry; defaults to `config.settings.local`. |

API routes are wired in `config/urls.py`: `/api/` includes `apps.users.urls` (e.g. profiles resource). Admin lives at `/admin/`.

## Setup

1. Create a virtual environment and install dev deps:

   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements/local.txt
   ```

2. Copy environment template and fill in values (especially `DATABASE_URL` from Supabase): `cp .env.example .env` (or `copy .env.example .env` on Windows).

3. Apply migrations and run the server:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

For production, set `DJANGO_SETTINGS_MODULE=config.settings.production`, use `requirements/production.txt`, and set `SECRET_KEY`, `ALLOWED_HOSTS`, and a valid `DATABASE_URL` via the host environment or `.env` (do not commit `.env`).
