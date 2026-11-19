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

## Deploy to Heroku

Heroku hosting and its database may involve paid usage. Check the current plan and database pricing with a parent/guardian before enabling billing.

You will need:
- A Heroku account and the Heroku CLI installed
- Git installed
- A Heroku Postgres database attached to the app

From Command Prompt or PowerShell in the project folder:

```bat
heroku login
git init
git add .
git commit -m "Prepare lowkey for launch"
heroku create choose-a-unique-app-name --stack heroku-26
heroku addons:create heroku-postgresql:essential-0
```

Set production settings. First generate a strong secret key locally:

```bat
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the generated value, then set it on Heroku:

```bat
heroku config:set DEBUG=False SECRET_KEY="paste-your-generated-key-here"
```

Deploy the `main` branch:

```bat
git branch -M main
git push heroku main
```

The `release` command in the Procfile automatically runs database migrations during deployment. When the deploy finishes, create the site's admin account:

```bat
heroku run python manage.py createsuperuser
```

Then open the site:

```bat
heroku open
```

Useful troubleshooting commands:

```bat
heroku logs --tail
heroku releases:output
heroku config
```

### Important deployment notes

- The Heroku Postgres database starts empty. Your local SQLite database is not uploaded, and this update deliberately excludes `db.sqlite3` so your local data stays safe.
- Keep `SECRET_KEY` private. Never commit it into your code.
- Do not set `DEBUG=True` on the public site.
- Heroku automatically uses the `DATABASE_URL` value from the attached Postgres add-on.
- The app uses the `.python-version` file to select Python 3.12 on Heroku.
- Before inviting lots of people, consider adding email verification, password-reset email delivery, moderation/reporting tools, rate limits, and privacy/terms pages.

## Project layout

- `config/` — Django project settings and URLs
- `polls/` — models, forms, views, admin, tests, and migration files
- `templates/` — HTML templates
- `polls/static/polls/style.css` — site styling
- `Procfile` — Heroku release and web processes
- `.python-version` — Heroku Python runtime
