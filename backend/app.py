import os
import uuid
import base64
from datetime import datetime
from flask import Flask, request, jsonify, session, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "secret123")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# -------- MODELS --------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password = db.Column(db.String(100), nullable=False)

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
        return {
            "id": self.id,
            "username": self.username,
            "text": self.text,
            "mood": self.mood,
            "date": self.date_str or self.created_at.strftime("%b %d, %Y"),
            "day": self.day_str or self.created_at.strftime("%A"),
            "media_url": self.media_url,
            "created_at": self.created_at.isoformat()
        }

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

    user = User(username=username, email=email, password=password)
    db.session.add(user)
    db.session.commit()
    session["user"] = user.username
    return jsonify({"success": True, "message": "Registered successfully", "user": user.to_dict()}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session["user"] = user.username
        return jsonify({"success": True, "message": "Login successful", "user": user.to_dict()})
    return jsonify({"success": False, "message": "Invalid username or password"}), 401

@app.route("/api/logout", methods=["GET", "POST"])
def logout():
    session.pop("user", None)
    return jsonify({"success": True, "message": "Logged out"})

@app.route("/api/upload-media", methods=["POST"])
def upload_media():
    try:
        # 1. Check if multipart file was uploaded
        if "file" in request.files:
            file = request.files["file"]
            if file.filename:
                ext = file.filename.split(".")[-1].lower() or "webm"
                filename = f"webcam_{uuid.uuid4().hex[:10]}.{ext}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                url = f"/static/uploads/{filename}"
                return jsonify({"success": True, "url": url})

        # 2. Check if base64 image data was sent via JSON
        data = request.get_json(silent=True) or {}
        image_data = data.get("image_base64")
        if image_data and "," in image_data:
            header, encoded = image_data.split(",", 1)
            ext = "png"
            if "jpeg" in header or "jpg" in header:
                ext = "jpg"
            elif "webm" in header:
                ext = "webm"
            filename = f"snapshot_{uuid.uuid4().hex[:10]}.{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(encoded))
            url = f"/static/uploads/{filename}"
            return jsonify({"success": True, "url": url})

        return jsonify({"success": False, "message": "No valid media provided"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/entries", methods=["GET", "POST"])
def handle_entries():
    current_user = session.get("user")
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"success": False, "message": "Content cannot be empty"}), 400

        entry = Entry(
            username=current_user,
            text=text,
            mood=data.get("mood", "😊"),
            date_str=data.get("date"),
            day_str=data.get("day"),
            media_url=data.get("media_url")
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({"success": True, "entry": entry.to_dict()}), 201

    entries = Entry.query.order_by(Entry.id.desc()).all()
    return jsonify({"success": True, "entries": [e.to_dict() for e in entries]})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
