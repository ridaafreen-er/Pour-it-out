import os
import uuid
import base64
import hmac
import secrets
import shutil
from datetime import datetime
from flask import Flask, request, jsonify, session, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from dotenv import load_dotenv

# Load environment variables from .env files
load_dotenv()
load_dotenv(".env.local")
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

IS_VERCEL = os.environ.get("VERCEL") == "1"
PROJECT_INSTANCE_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "instance"))
PUBLIC_STATIC_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "static"))
app = Flask(
    __name__,
    instance_path=PROJECT_INSTANCE_FOLDER,
    static_folder=PUBLIC_STATIC_FOLDER,
    static_url_path="/static",
)

def get_secret_key():
    configured_key = os.environ.get("SECRET_KEY", "").strip()
    example_key = "retro-pixel-journal-secret-2026"
    if len(configured_key) >= 32 and configured_key != example_key:
        return configured_key
    if IS_VERCEL:
        raise RuntimeError("Set a random SECRET_KEY of at least 32 characters in Vercel project settings.")

    os.makedirs(app.instance_path, exist_ok=True)
    secret_path = os.path.join(app.instance_path, "secret_key")
    try:
        with open(secret_path, "x", encoding="utf-8") as secret_file:
            secret_file.write(secrets.token_hex(32))
    except FileExistsError:
        pass

    with open(secret_path, "r+", encoding="utf-8") as secret_file:
        key = secret_file.read().strip()
        if len(key) < 64:
            key = secrets.token_hex(32)
            secret_file.seek(0)
            secret_file.write(key)
            secret_file.truncate()
    if os.name != "nt":
        os.chmod(secret_path, 0o600)
    print("[Security Notice] Using a persistent generated session key; configure a private SECRET_KEY to override it.")
    return key


app.config["SECRET_KEY"] = get_secret_key()
app.config["SESSION_COOKIE_SECURE"] = IS_VERCEL
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
PRIVATE_UPLOAD_FOLDER = os.path.join(app.instance_path, "private_uploads")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
if not IS_VERCEL:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(PRIVATE_UPLOAD_FOLDER, exist_ok=True)


def migrate_public_uploads():
    for filename in os.listdir(UPLOAD_FOLDER):
        source_path = os.path.join(UPLOAD_FOLDER, filename)
        target_path = os.path.join(PRIVATE_UPLOAD_FOLDER, filename)
        if os.path.isfile(source_path) and not os.path.exists(target_path):
            shutil.move(source_path, target_path)


@app.before_request
def block_public_upload_access():
    if request.path.startswith("/static/uploads/"):
        return "Not Found", 404

ACTIVE_DB_ENGINE = "SQLite"

def configure_database():
    global ACTIVE_DB_ENGINE
    use_mysql = os.environ.get("USE_MYSQL", "true").lower() in ("true", "1", "yes")
    custom_uri = os.environ.get("DATABASE_URL")
    if custom_uri:
        ACTIVE_DB_ENGINE = "Custom"
        if custom_uri.startswith("mysql://"):
            custom_uri = custom_uri.replace("mysql://", "mysql+pymysql://", 1)
        return custom_uri
    if IS_VERCEL:
        raise RuntimeError("Set DATABASE_URL to a hosted MySQL database in Vercel project settings.")

    if use_mysql:
        mysql_user = os.environ.get("MYSQL_USER", "root")
        mysql_pwd = os.environ.get("MYSQL_PASSWORD", "").strip()
        mysql_host = os.environ.get("MYSQL_HOST", "127.0.0.1")
        mysql_port = int(os.environ.get("MYSQL_PORT", 3306))
        mysql_db = os.environ.get("MYSQL_DB", "journal_app")

        # Only attempt MySQL connection if password is provided or configured
        if mysql_pwd or os.environ.get("FORCE_MYSQL") == "true":
            try:
                import pymysql
                # Connect to MySQL Server to create database if not present
                conn = pymysql.connect(
                    host=mysql_host,
                    user=mysql_user,
                    password=mysql_pwd,
                    port=mysql_port,
                    connect_timeout=3
                )
                with conn.cursor() as cur:
                    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{mysql_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                conn.close()
                print(f"[Database] Successfully connected to MySQL Server (database: '{mysql_db}')!")
                ACTIVE_DB_ENGINE = f"MySQL ({mysql_db})"
                return f"mysql+pymysql://{mysql_user}:{mysql_pwd}@{mysql_host}:{mysql_port}/{mysql_db}?charset=utf8mb4"
            except Exception as e:
                print(f"[Database Notice] MySQL connection not ready ({e}). Falling back to SQLite.")
                ACTIVE_DB_ENGINE = "SQLite (fallback)"
                return "sqlite:///database.db"
        else:
            print("[Database Notice] MySQL password not set in .env yet. Using SQLite database.db.")
            ACTIVE_DB_ENGINE = "SQLite"
            return "sqlite:///database.db"

    ACTIVE_DB_ENGINE = "SQLite"
    return "sqlite:///database.db"

app.config["SQLALCHEMY_DATABASE_URI"] = configure_database()
db = SQLAlchemy(app)

# -------- MODELS --------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email}

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=True)
    text = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(20), default="😊")
    date_str = db.Column(db.String(100), nullable=True)
    day_str = db.Column(db.String(50), nullable=True)
    media_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        media_filename = secure_filename(os.path.basename((self.media_url or "").split("?", 1)[0]))
        return {
            "id": self.id,
            "username": self.username,
            "text": self.text,
            "mood": self.mood,
            "date": self.date_str or self.created_at.strftime("%b %d, %Y"),
            "day": self.day_str or self.created_at.strftime("%A"),
            "media_url": f"/api/media/{media_filename}" if media_filename else None,
            "created_at": self.created_at.isoformat()
        }

class MediaUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False, index=True)

# -------- PAGE ROUTES --------
@app.route("/")
@app.route("/home")
@app.route("/home.html")
@app.route("/Home.html")
def home():
    return render_template("home.html")

@app.route("/register")
@app.route("/register.html")
def register_page():
    return render_template("register.html")

@app.route("/login")
@app.route("/login.html")
def login_page():
    return render_template("login.html")

@app.route("/journal")
@app.route("/journal.html")
def journal_page():
    return render_template("journal.html")

# -------- API ROUTES --------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"success": False, "message": "Username already taken"}), 409

    user = User(username=username, email=email, password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    session.clear()
    session["user"] = user.username
    return jsonify({"success": True, "message": "Registered successfully", "user": user.to_dict()}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()
    password_matches = False
    if user and user.password.startswith(("scrypt:", "pbkdf2:")):
        password_matches = check_password_hash(user.password, password)
    elif user and hmac.compare_digest(user.password, password):
        user.password = generate_password_hash(password)
        db.session.commit()
        password_matches = True

    if user and password_matches:
        session.clear()
        session["user"] = user.username
        return jsonify({"success": True, "message": "Login successful", "user": user.to_dict()})
    return jsonify({"success": False, "message": "Invalid username or password"}), 401

@app.route("/api/logout", methods=["GET", "POST"])
def logout():
    session.pop("user", None)
    return jsonify({"success": True, "message": "Logged out"})

@app.route("/api/session", methods=["GET"])
def get_current_session():
    username = session.get("user")
    if not username:
        return jsonify({"success": False, "message": "Please sign in"}), 401
    return jsonify({"success": True, "username": username})

@app.route("/api/upload-media", methods=["POST"])
def upload_media():
    if IS_VERCEL:
        return jsonify({"success": False, "message": "Media uploads are stored in this browser on Vercel"}), 410
    try:
        current_user = session.get("user")
        if not current_user:
            return jsonify({"success": False, "message": "Please sign in to upload media"}), 401

        if "file" in request.files:
            file = request.files["file"]
            if file.filename:
                extension = os.path.splitext(secure_filename(file.filename))[1].lower().lstrip(".")
                if extension not in {"png", "jpg", "jpeg", "webm", "mp4", "ogg"}:
                    return jsonify({"success": False, "message": "Unsupported media type"}), 400
                media_bytes = file.read(24 * 1024 * 1024 + 1)
                if len(media_bytes) > 24 * 1024 * 1024:
                    return jsonify({"success": False, "message": "Media file is too large"}), 413
                return store_private_upload(media_bytes, extension, current_user)

        data = request.get_json(silent=True) or {}
        image_data = data.get("image_base64")
        if image_data and "," in image_data:
            header, encoded = image_data.split(",", 1)
            header = header.lower()
            extension = next((ext for marker, ext in (
                ("image/png", "png"),
                ("image/jpeg", "jpg"),
                ("video/webm", "webm"),
                ("video/mp4", "mp4"),
                ("video/ogg", "ogg"),
            ) if marker in header), None)
            if not extension:
                return jsonify({"success": False, "message": "Unsupported media type"}), 400
            media_bytes = base64.b64decode(encoded, validate=True)
            if len(media_bytes) > 24 * 1024 * 1024:
                return jsonify({"success": False, "message": "Media file is too large"}), 413
            return store_private_upload(media_bytes, extension, current_user)

        return jsonify({"success": False, "message": "No valid media provided"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def store_private_upload(media_bytes, extension, username):
    filename = f"{uuid.uuid4().hex}.{extension}"
    filepath = os.path.join(PRIVATE_UPLOAD_FOLDER, filename)
    with open(filepath, "wb") as media_file:
        media_file.write(media_bytes)
    db.session.add(MediaUpload(filename=filename, username=username))
    db.session.commit()
    return jsonify({"success": True, "url": f"/api/media/{filename}"})


@app.route("/api/media/<filename>")
def get_private_media(filename):
    if IS_VERCEL:
        return jsonify({"success": False, "message": "Media is stored in this browser on Vercel"}), 404
    current_user = session.get("user")
    if not current_user:
        return jsonify({"success": False, "message": "Please sign in to access media"}), 401
    if secure_filename(filename) != filename:
        return jsonify({"success": False, "message": "Media not found"}), 404
    upload = MediaUpload.query.filter_by(filename=filename, username=current_user).first()
    if not upload:
        return jsonify({"success": False, "message": "Media not found"}), 404
    return send_from_directory(PRIVATE_UPLOAD_FOLDER, filename)

@app.route("/api/entries", methods=["GET", "POST"])
def handle_entries():
    current_user = session.get("user")
    if not current_user:
        return jsonify({"success": False, "message": "Please sign in to access account entries"}), 401

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"success": False, "message": "Content cannot be empty"}), 400

        media_url = data.get("media_url")
        if media_url:
            media_filename = secure_filename(os.path.basename(str(media_url).split("?", 1)[0]))
            owned_upload = MediaUpload.query.filter_by(filename=media_filename, username=current_user).first()
            if not media_filename or not owned_upload:
                return jsonify({"success": False, "message": "Media does not belong to this account"}), 403
            media_url = f"/api/media/{media_filename}"

        entry = Entry(
            username=current_user,
            text=text,
            mood=data.get("mood", "😊"),
            date_str=data.get("date"),
            day_str=data.get("day"),
            media_url=media_url
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({"success": True, "entry": entry.to_dict()}), 201

    entries = Entry.query.filter_by(username=current_user).order_by(Entry.id.desc()).all()
    return jsonify({"success": True, "username": current_user, "entries": [e.to_dict() for e in entries]})

@app.route("/api/entries/<int:entry_id>", methods=["DELETE"])
def delete_entry(entry_id):
    current_user = session.get("user")
    if not current_user:
        return jsonify({"success": False, "message": "Please sign in to delete entries"}), 401

    entry = Entry.query.filter_by(id=entry_id, username=current_user).first()
    if entry:
        db.session.delete(entry)
        db.session.commit()
        return jsonify({"success": True, "message": "Entry deleted from database"})
    return jsonify({"success": False, "message": "Entry not found"}), 404

@app.route("/api/db-status", methods=["GET"])
def get_db_status():
    return jsonify({
        "success": True,
        "engine": ACTIVE_DB_ENGINE,
        "database_uri": str(app.config["SQLALCHEMY_DATABASE_URI"]).split("@")[-1] if "@" in str(app.config["SQLALCHEMY_DATABASE_URI"]) else str(app.config["SQLALCHEMY_DATABASE_URI"]),
        "tables": ["user", "entry"]
    })


def initialize_schema():
    db.create_all()
    if db.engine.dialect.name == "mysql":
        password_column = next(column for column in inspect(db.engine).get_columns("user") if column["name"] == "password")
        if password_column["type"].length < 255:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE `user` MODIFY COLUMN `password` VARCHAR(255) NOT NULL"))


@app.cli.command("init-db")
def initialize_database_command():
    with app.app_context():
        initialize_schema()
    print("Database schema is ready.")

if __name__ == "__main__":
    with app.app_context():
        initialize_schema()
        migrate_public_uploads()
    debug_enabled = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    app.run(debug=debug_enabled)
