LOWKEY SOCIAL + CHAT + DAILY ACTIVE TIME UPDATE

Adds text-first social posts, likes/comments on text posts, private one-to-one chats, and a two-hour active-use timer.

INSTALL
1. Stop local server (Ctrl+C).
2. Back up db.sqlite3.
3. Extract into the existing polling project folder and replace files. Keep .venv and db.sqlite3.
4. Run: .venv\Scripts\activate.bat
   python manage.py migrate
   python manage.py check
   python manage.py test
   python manage.py runserver

CHAT
- Chats are one-to-one and visible only to participants.
- Starting a chat requires a mutual follow (both people follow each other).
- Messages refresh about every five seconds; this first version does not use WebSockets.

ACTIVE TIME
- Two hours per local calendar day.
- Counts only while the page is visible and there has been activity within the last 60 seconds.
- At the limit, a blocking screen offers another five minutes; it returns when those minutes are used. Repeated extensions are possible.
- Stored in browser localStorage: per browser/device, not tamper-proof, and can be reset by clearing site data or using another browser/device.

DEPLOY
After local checks pass: git add . && git commit -m "Add social posts chat and active time limit" && git push
Render build command must include: python manage.py migrate --noinput
