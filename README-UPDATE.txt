LOWKEY FINAL UPDATE

1. Stop your server with Ctrl+C.
2. Back up db.sqlite3.
3. Extract this update into C:\Users\Uthmaan\Desktop\polling and allow source files to replace the old ones. Keep your .venv and existing db.sqlite3.
4. Open Command Prompt in that folder and run:

.venv\Scripts\activate.bat
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver

Open http://127.0.0.1:8000/

IMPORTANT:
- Do not run makemigrations for this update. Migration 0003 is already included.
- The new migration enforces one vote per user per poll. If old data contains duplicate votes in one poll, it keeps the earliest vote.
- The update ZIP intentionally does not include db.sqlite3 or your .venv. Your local database is preserved.
- Heroku deployment steps are in README.md. Heroku hosting/database use may cost money; check pricing and get parent/guardian approval before enabling billing.
