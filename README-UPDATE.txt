LOWKEY DISCOVERY + DESIGN UPDATE

LOCAL UPDATE
1. Stop the local server with Ctrl+C.
2. Back up db.sqlite3.
3. Extract this ZIP into C:\Users\Uthmaan\Desktop\polling and allow files to replace existing source files.
4. Keep your .venv and db.sqlite3. They are not included in this ZIP.
5. In Command Prompt, run:

.venv\Scripts\activate.bat
python manage.py check
python manage.py test
python manage.py runserver

Open http://127.0.0.1:8000/ and test the Explore page, category chips, search, trending cards, poll creation, voting, results, and mobile layout.

WHAT CHANGED
- A redesigned Explore page with a clearer lowkey identity.
- Trending polls based on actual votes.
- Community counts for questions, members, and votes.
- Category quick filters, search, and sorting.
- Nine polls per page with pagination.
- Improved poll detail sharing and result links.
- More polished responsive layouts and reduced-motion accessibility.
- Render domains are included in Django's default allowed hosts and CSRF origins.
- No database migration is required for this update.

PUSH THE UPDATE TO GITHUB
From the project folder, run:

git add .
git commit -m "Refresh lowkey discovery and design"
git push

RENDER
If your Render service is connected to this GitHub repository with automatic deploys enabled, the push should start a new deployment. Check that your Build Command is:

pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate --noinput

And your Start Command is:

gunicorn config.wsgi:application

Do not change your DATABASE_URL or SECRET_KEY. Do not upload db.sqlite3, .venv, or .env.
