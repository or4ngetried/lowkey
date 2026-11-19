# lowkey — polling site

A Django polling site with accounts, profiles, public and private polls, poll discovery, and results.

## Included features

- Create public polls or private polls shared by a unique link
- Add 2–100 answer options to a poll
- Sign up, log in, and edit a short profile bio
- Search public polls, filter by category, and sort by newest/popular/oldest
- Vote while signed in
- One vote per account per poll, enforced by a database constraint
- View vote counts and percentages
- See your own polls and copy private share links
- Responsive layout with a simple lowkey visual style
- Django admin for site management

## Run locally (Windows)

Open Command Prompt in the folder containing `manage.py`:

```bat
.venv\Scripts\activate.bat
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

Open http://127.0.0.1:8000/

Create an admin account if you want to use the admin page:

```bat
python manage.py createsuperuser
```

## Updating an existing copy

1. Stop the local server with `Ctrl+C`.
2. Make a backup copy of `db.sqlite3`.
3. Extract the update into the project folder and allow the included source files to replace the old ones. Keep your `.venv` and your existing `db.sqlite3`.
4. Activate the environment and run:

```bat
.venv\Scripts\activate.bat
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

The included `0003` migration adds a poll reference to each vote and enforces one vote per user per poll. If the old database contains more than one vote by the same user in the same poll, the migration keeps the earliest vote and removes the later duplicates. It does not delete accounts or polls.

## Deploy to Render

The project can run on Render as a Django web service connected to PostgreSQL. Free services and databases have usage and retention limits; check Render's current pricing and database expiration terms before relying on it for permanent data.

### Render web service settings

- Runtime: Python 3
- Branch: `main`
- Build command: `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate --noinput`
- Start command: `gunicorn config.wsgi:application`
- Instance: Free for testing

### Environment variables

Set these in the Render web service's Environment tab:

- `DEBUG=False`
- `SECRET_KEY` — generate a strong random secret; keep it private
- `DATABASE_URL` — the database's Internal Database URL
- `ALLOWED_HOSTS=.onrender.com`
- `CSRF_TRUSTED_ORIGINS=https://*.onrender.com`

The Render PostgreSQL database must be in the same region as the web service. Do not put `db.sqlite3`, `.venv`, `.env`, the secret key, or database credentials in GitHub.

### Updating the live site

After changing code locally, run tests, then push the changes:

```bash
git add .
git commit -m "Describe the update"
git push
```

If automatic deploys are enabled in Render, the new commit will trigger a deployment. Otherwise, use Manual Deploy → Deploy latest commit in the Render dashboard.

The free Render web service may spin down when idle. Free PostgreSQL plans have time limits and should not be treated as permanent storage. Check the current Render pricing and retention policy before inviting a large audience or storing important data.

## Project layout

- `config/` — Django project settings and URLs
- `polls/` — models, forms, views, admin, tests, and migration files
- `templates/` — HTML templates
- `polls/static/polls/style.css` — site styling
- `Procfile` — Heroku release and web processes
- `.python-version` — Heroku Python runtime
