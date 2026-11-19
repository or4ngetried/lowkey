# lowkey

A Django-powered social app built around text posts, polls, following, comments, and private one-to-one messaging.

## Local setup

```bat
.venv\Scripts\activate.bat
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

## New in this update

- Text-first social posts in the combined feed
- Likes and comments on text posts
- One-to-one private messages between mutual followers
- Inbox, unread counts, and near-live message refresh
- Two hours of active use per day, with repeatable five-minute extensions

The active-use reminder is stored in browser local storage and applies per account/browser. It is a self-management feature, not tamper-proof enforcement.

## Render deployment

Push changes to GitHub. Render should deploy automatically. Ensure the build command includes:

```bash
pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate --noinput
```

Start command:

```bash
gunicorn config.wsgi:application
```
