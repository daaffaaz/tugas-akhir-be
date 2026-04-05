# Backend (Django REST API)

Django 5 project with **Django REST Framework**, **JWT (SimpleJWT)**, **PostgreSQL** (Supabase via `DATABASE_URL`), and **CORS** for a Next.js frontend. Domain apps live under `apps/`.

## Project layout

| Path | Purpose |
|------|--------|
| `config/` | Django project: URLs, WSGI/ASGI, `settings/`. |
| `config/settings/base.py` | Shared settings (DB, DRF, JWT, CORS, `AUTH_USER_MODEL`). |
| `apps/users/` | Custom `User` (UUID), auth (`/api/auth/...`), profile (`/api/users/profile/`). |
| `apps/questionnaires/` | Questions, user answers, onboarding endpoints. |
| `apps/courses/` | Platforms, courses, tags, catalog API, `import_courses`. |
| `apps/learning_paths/` | Learning paths, path courses, bulk update, progress toggle. |
| `data/` | Sample questionnaire CSV for `import_questions`. |
| `requirements/` | `base.txt`, `local.txt`, `production.txt`. |

## Setup

1. Create a venv and install deps:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements/local.txt
   ```

2. Copy `.env.example` to `.env` and set `SECRET_KEY`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`, etc.

3. Migrate, seed questions, import courses (optional), create superuser:

   ```bash
   python manage.py migrate
   python manage.py import_questions --file "C:\Users\user\Documents\dev\ta scrap\pertanyaan kuesioner.csv"
   python manage.py import_courses --platform udemy --file "C:\Users\user\Documents\dev\ta scrap\udemy_courses_20260316_140009.csv"
   python manage.py import_courses --platform icei --file "C:\Users\user\Documents\dev\ta scrap\icei_courses_20260223_153052 - icei_courses_20260223_153052.csv"
   python manage.py createsuperuser
   python manage.py runserver
   ```

## API overview (all under `/api/`)

| Method | Path | Notes |
|--------|------|--------|
| POST | `/auth/register/` | Register; returns `access`, `refresh`. |
| POST | `/auth/login/` | Body: `email`, `password`. |
| POST | `/auth/token/refresh/` | Refresh JWT. |
| GET | `/questions/` | List questionnaire questions. |
| POST | `/users/questionnaire/` | Submit all answers (JSON array). |
| PATCH | `/users/questionnaire/` | Partial answer updates (after POST). |
| GET/PATCH | `/users/profile/` | Profile read/update. |
| GET | `/courses/` | Catalog: search, filters, pagination. |
| GET/POST | `/learning-paths/` | List/create paths. |
| GET | `/learning-paths/<uuid>/` | Path detail + courses. |
| PUT | `/learning-paths/<uuid>/bulk-update/` | Replace path structure transactionally. |
| PATCH | `/learning-paths/courses/<uuid>/toggle-complete/` | Toggle completion (`LearningPathCourse` id). |

JWT required for protected routes. Middleware returns `403` if the user is authenticated but has not completed the onboarding questionnaire (except auth, listing questions, and submitting the questionnaire).

Browsable API login (session) for development: `/api/drf-auth/`.

For production, set `DJANGO_SETTINGS_MODULE=config.settings.production` and use `requirements/production.txt`.
