
import os
from datetime import timedelta

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


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)


class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    diagnosis = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.String(500))


def role_required(*allowed_roles):
    def decorator(function):
        from functools import wraps

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


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "application": "Healthcare DevSecOps"})


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if role not in ["patient", "doctor"]:
        return jsonify({"error": "Invalid role"}), 400

    if len(password) < 12:
        return jsonify({"error": "Password must contain at least 12 characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "access_token": token,
        "role": user.role
    })


@app.route("/records", methods=["GET"])
@role_required("patient", "doctor")
def get_records():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    if user.role == "patient":
        records = MedicalRecord.query.filter_by(patient_id=user_id).all()
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


@app.route("/records", methods=["POST"])
@role_required("doctor")
def create_record():
    data = request.get_json(silent=True) or {}

    patient_id = data.get("patient_id")
    diagnosis = data.get("diagnosis", "").strip()
    notes = data.get("notes", "").strip()

    if not patient_id or not diagnosis:
        return jsonify({"error": "Patient ID and diagnosis required"}), 400

    patient = db.session.get(User, patient_id)

    if not patient or patient.role != "patient":
        return jsonify({"error": "Patient not found"}), 404

    record = MedicalRecord(
        patient_id=patient_id,
        diagnosis=diagnosis,
        notes=notes
    )

    db.session.add(record)
    db.session.commit()

    return jsonify({"message": "Record created", "id": record.id}), 201


@app.route("/records/<int:record_id>", methods=["DELETE"])
@role_required("doctor")
def delete_record(record_id):
    record = db.session.get(MedicalRecord, record_id)

    if not record:
        return jsonify({"error": "Record not found"}), 404

    db.session.delete(record)
    db.session.commit()

    return jsonify({"message": "Record deleted"})


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)