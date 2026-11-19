
import os
from datetime import timedelta
from functools import wraps

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///healthcare.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)

db = SQLAlchemy(app)
jwt = JWTManager(app)


# Database models

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)


class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
    diagnosis = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.String(500))


# Role-based access control

def role_required(*allowed_roles):
    def decorator(function):

        @wraps(function)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = db.session.get(User, int(user_id))

            if not user or user.role not in allowed_roles:
                return jsonify({"error": "Access denied"}), 403

            return function(*args, **kwargs)

        return wrapper

    return decorator


# Health API

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "application": "Healthcare DevSecOps"
    })


# User registration

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "")

    if not username or not password:
        return jsonify({
            "error": "Username and password required"
        }), 400

    if role not in ["patient", "doctor"]:
        return jsonify({
            "error": "Invalid role"
        }), 400

    if len(password) < 12:
        return jsonify({
            "error": "Password must contain at least 12 characters"
        }), 400

    if User.query.filter_by(username=username).first():
        return jsonify({
            "error": "Username already exists"
        }), 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "User registered successfully"
    }), 201


# User login

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(
        user.password_hash, password
    ):
        return jsonify({
            "error": "Invalid credentials"
        }), 401

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "access_token": token,
        "role": user.role
    })


# Retrieve medical records

@app.route("/records", methods=["GET"])
@role_required("patient", "doctor")
def get_records():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user.role == "patient":
        records = MedicalRecord.query.filter_by(
            patient_id=user_id
        ).all()
    else:
        records = MedicalRecord.query.all()

    return jsonify([
        {
            "id": record.id,
            "patient_id": record.patient_id,
            "diagnosis": record.diagnosis,
            "notes": record.notes
        }
        for record in records
    ])


# Create medical record

@app.route("/records", methods=["POST"])
@role_required("doctor")
def create_record():
    data = request.get_json(silent=True) or {}

    patient_id = data.get("patient_id")
    diagnosis = data.get("diagnosis", "").strip()
    notes = data.get("notes", "").strip()

    if not patient_id or not diagnosis:
        return jsonify({
            "error": "Patient ID and diagnosis required"
        }), 400

    patient = db.session.get(User, patient_id)

    if not patient or patient.role != "patient":
        return jsonify({
            "error": "Patient not found"
        }), 404

    record = MedicalRecord(
        patient_id=patient_id,
        diagnosis=diagnosis,
        notes=notes
    )

    db.session.add(record)
    db.session.commit()

    return jsonify({
        "message": "Record created",
        "id": record.id
    }), 201


# Delete medical record

@app.route("/records/<int:record_id>", methods=["DELETE"])
@role_required("doctor")
def delete_record(record_id):
    record = db.session.get(MedicalRecord, record_id)

    if not record:
        return jsonify({
            "error": "Record not found"
        }), 404

    db.session.delete(record)
    db.session.commit()

    return jsonify({
        "message": "Record deleted"
    })


# Healthcare website homepage

@app.route("/", methods=["GET"])
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HealthCare | Secure Healthcare Management</title>

        <style>
            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f3f7fb;
                color: #243447;
            }

            header {
                background: #087f8c;
                color: white;
                padding: 22px 8%;
            }

            header h2 {
                margin: 0;
            }

            .hero {
                text-align: center;
                padding: 85px 20px;
                background: white;
            }

            .hero h1 {
                color: #087f8c;
                font-size: 40px;
            }

            .hero p {
                font-size: 18px;
                color: #64748b;
            }

            .button {
                display: inline-block;
                margin-top: 20px;
                padding: 13px 25px;
                background: #087f8c;
                color: white;
                text-decoration: none;
                border-radius: 6px;
            }

            .features {
                display: flex;
                justify-content: center;
                gap: 25px;
                flex-wrap: wrap;
                padding: 45px 20px;
            }

            .card {
                background: white;
                padding: 25px;
                width: 260px;
                border-radius: 10px;
                box-shadow: 0 3px 12px #00000010;
                text-align: center;
            }

            footer {
                text-align: center;
                padding: 22px;
                background: #e5eef2;
            }
        </style>
    </head>

    <body>

        <header>
            <h2>HealthCare+</h2>
        </header>

        <section class="hero">
            <h1>Healthcare Made Secure and Simple</h1>

            <p>
                A secure healthcare management system
                designed to manage patient information
                and medical records.
            </p>

            <a class="button" href="/health">
                Check System Status
            </a>
        </section>

        <section class="features">

            <div class="card">
                <h3>Patient Management</h3>
                <p>Manage patient registrations and accounts.</p>
            </div>

            <div class="card">
                <h3>Medical Records</h3>
                <p>Organize and access medical records securely.</p>
            </div>

            <div class="card">
                <h3>Secure Access</h3>
                <p>Role-based authentication for patients and doctors.</p>
            </div>

        </section>

        <footer>
            Healthcare DevSecOps Project | Secure Healthcare Management
        </footer>

    </body>
    </html>
    """


# Local development database initialization
# Docker uses init_db.py to initialize the database once
# before Gunicorn starts.

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="127.0.0.1", port=5000)
