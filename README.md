# गावफलक — Village Notice Board

A simple website where anyone can post a notice (with a photo, no login needed)
and everyone in the village can browse or search it — filterable by category
(Event, Alert, Lost & Found, Announcement, Other).

## Run it locally

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

## Deploying it live (free)

**Important first:** this app stores notices in a local SQLite file
(`board.db`) and uploaded photos in `static/uploads/`. Some free hosts wipe
local files on every redeploy/restart — fine for a demo, but you'll lose data.
Two solid free options that keep your data:

### Option A — Render.com (easiest, free web service + free persistent disk on paid tier)
1. Push this folder to a GitHub repo.
2. On Render: **New → Web Service**, connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Render's free web services use ephemeral disk — notices/photos reset on
   redeploy. To keep data permanently, add a small **Persistent Disk**
   (paid, a couple dollars/month) mounted at `/opt/render/project/src` and
   point `DB_PATH`/`UPLOAD_DIR` there, or upgrade to a plan that supports it.

### Option B — PythonAnywhere (free tier, keeps your files)
1. Create a free account at pythonanywhere.com.
2. Upload this folder (or `git clone` it) into your account via their Bash console.
3. `pip install --user -r requirements.txt`
4. Go to the **Web** tab → **Add a new web app** → **Flask** → point it at `app.py`.
5. Your SQLite DB and uploaded photos live on PythonAnywhere's disk and
   persist between reloads — good fit for a small village board.

Either way, once deployed, share the URL in your village WhatsApp/community
groups so people can post and read notices.

## Project structure

```
app.py                  Flask app: routes, DB setup
templates/               HTML pages (Jinja2)
static/css/style.css     Styling
static/uploads/          Uploaded notice photos (created automatically)
board.db                 SQLite database (created automatically on first run)
requirements.txt         Python dependencies
Procfile                 Start command for hosts like Render/Railway
```

## Notes on the "no login" design

Anyone can post — this keeps the barrier low for villagers. Moderation is
handled separately by a password-protected admin page (see below), so spam
or outdated notices can be removed without requiring everyone to sign up.

## Admin / moderation

There's an "Admin" link in the header. It leads to a login page guarded by
one shared password.

- **Default password:** `changeme` — change this before you deploy.
- Set it via an environment variable: `ADMIN_PASSWORD=your-real-password`
- Also set `SECRET_KEY` to a random string in production (used to sign the
  login session cookie): `SECRET_KEY=some-long-random-string`

On Render/PythonAnywhere, add both as environment variables in the host's
dashboard rather than hardcoding them in the code.

Once logged in at `/admin`, you'll see every notice in a table and can
delete any of them (this also removes their uploaded photo). Logging out
clears your admin session.
