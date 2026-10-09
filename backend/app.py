from flask import Flask, request, jsonify, session, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config["SECRET_KEY"] = "secret123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

db = SQLAlchemy(app)

# -------- MODELS --------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

@app.route("/")
def home():
    return render_template("home.html")
@app.route("/register")
def register_page():
    return render_template("register.html")
@app.route("/login")
def login_page():
    return render_template("login.html")
@app.route("/journal")
def journal_page():
    return render_template("journal.html")

# -------- ROUTES --------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    user = User(username=data["username"], password=data["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Registered"})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(
        username=data["username"],
        password=data["password"]
    ).first()

    if user:
        session["user"] = user.username
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route("/logout")
def logout():
    session.pop("user", None)
    return jsonify({"message": "Logged out"})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
