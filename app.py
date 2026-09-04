import os
import sqlite3
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, g, abort, session
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "board.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_LENGTH = 6 * 1024 * 1024  # 6 MB per upload

CATEGORIES = [
    ("event", "Event"),
    ("alert", "Alert"),
    ("lost_found", "Lost & Found"),
    ("announcement", "Announcement"),
    ("other", "Other"),
]
CATEGORY_KEYS = {c[0] for c in CATEGORIES}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
os.makedirs(UPLOAD_DIR, exist_ok=True)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            category TEXT NOT NULL,
            posted_by TEXT,
            image_filename TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    db.commit()
    db.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@app.route("/")
def index():
    category = request.args.get("category", "").strip()
    search = request.args.get("q", "").strip()

    query = "SELECT * FROM notices"
    conditions = []
    params = []

    if category and category in CATEGORY_KEYS:
        conditions.append("category = ?")
        params.append(category)

    if search:
        conditions.append("(title LIKE ? OR body LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"

    db = get_db()
    notices = db.execute(query, params).fetchall()

    return render_template(
        "index.html",
        notices=notices,
        categories=CATEGORIES,
        active_category=category,
        search=search,
    )


@app.route("/notice/<int:notice_id>")
def view_notice(notice_id):
    db = get_db()
    notice = db.execute("SELECT * FROM notices WHERE id = ?", (notice_id,)).fetchone()
    if notice is None:
        abort(404)
    return render_template("notice.html", notice=notice, categories=dict(CATEGORIES))


@app.route("/post", methods=["GET", "POST"])
def post_notice():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        category = request.form.get("category", "").strip()
        posted_by = request.form.get("posted_by", "").strip()

        errors = []
        if not title:
            errors.append("Please add a title.")
        if not body:
            errors.append("Please write the notice details.")
        if category not in CATEGORY_KEYS:
            errors.append("Please choose a category.")
        if len(title) > 150:
            errors.append("Title is too long (max 150 characters).")

        image_filename = None
        file = request.files.get("image")
        if file and file.filename:
            if not allowed_file(file.filename):
                errors.append("Image must be PNG, JPG, GIF, or WEBP.")
            else:
                ext = file.filename.rsplit(".", 1)[1].lower()
                safe_name = secure_filename(f"{datetime.utcnow().timestamp()}.{ext}")
                if not errors:
                    file.save(os.path.join(UPLOAD_DIR, safe_name))
                    image_filename = safe_name

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "post.html",
                categories=CATEGORIES,
                form=request.form,
            )

        db = get_db()
        db.execute(
            """
            INSERT INTO notices (title, body, category, posted_by, image_filename, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                body,
                category,
                posted_by or "Anonymous",
                image_filename,
                datetime.utcnow().isoformat(),
            ),
        )
        db.commit()
        flash("Your notice is posted on the board.", "success")
        return redirect(url_for("index"))

    return render_template("post.html", categories=CATEGORIES, form={})


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password and password == ADMIN_PASSWORD:
            session["is_admin"] = True
            flash("Logged in as admin.", "success")
            next_url = request.args.get("next") or url_for("admin_dashboard")
            return redirect(next_url)
        flash("Wrong password.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    flash("Logged out.", "success")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    notices = db.execute("SELECT * FROM notices ORDER BY created_at DESC").fetchall()
    return render_template("admin_dashboard.html", notices=notices, categories=dict(CATEGORIES))


@app.route("/notice/<int:notice_id>/delete", methods=["POST"])
@admin_required
def delete_notice(notice_id):
    db = get_db()
    notice = db.execute("SELECT * FROM notices WHERE id = ?", (notice_id,)).fetchone()
    if notice is None:
        abort(404)
    if notice["image_filename"]:
        image_path = os.path.join(UPLOAD_DIR, notice["image_filename"])
        if os.path.exists(image_path):
            os.remove(image_path)
    db.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
    db.commit()
    flash("Notice removed from the board.", "success")
    return redirect(url_for("admin_dashboard"))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
else:
    init_db()
