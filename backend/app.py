"""Face Verification Authentication System - Flask backend entry point."""

import base64
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from auth import generate_token, get_current_student_id, hash_password, verify_password
from face_service import compare_faces, encode_face_from_bytes, encoding_to_bytes
from models import FaceData, LoginLog, MoodleSession, Student, db
from moodle_integration import create_moodle_session_token, get_or_create_moodle_user

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    # ── Database ──────────────────────────────────────────────────────────────
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@db:5432/face_verification",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ── JWT ───────────────────────────────────────────────────────────────────
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(os.getenv("JWT_EXPIRY_HOURS", "1")) * 3600

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})

    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=os.getenv("REDIS_URL", "memory://"),
    )

    # ── Create tables ─────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()

    # ── Helper ────────────────────────────────────────────────────────────────
    def _student_or_404(student_db_id: int):
        student = db.session.get(Student, student_db_id)
        if not student:
            return None, (jsonify({"error": "Student not found"}), 404)
        return student, None

    # ════════════════════════════════════════════════════════════════════════
    # Auth endpoints
    # ════════════════════════════════════════════════════════════════════════

    @app.post("/api/auth/register")
    @limiter.limit("10 per hour")
    def register():
        data = request.get_json(silent=True) or {}

        required = ("student_id", "name", "email", "password", "face_images")
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        if Student.query.filter(
            (Student.student_id == data["student_id"]) | (Student.email == data["email"])
        ).first():
            return jsonify({"error": "Student ID or email already registered"}), 409

        face_images: list = data["face_images"]
        if not isinstance(face_images, list) or not (1 <= len(face_images) <= 10):
            return jsonify({"error": "Provide between 1 and 10 face images"}), 400

        # Decode and encode face images
        encodings = []
        for idx, img_b64 in enumerate(face_images):
            try:
                img_bytes = base64.b64decode(img_b64)
            except Exception:
                return jsonify({"error": f"Invalid base64 for image {idx}"}), 400

            enc = encode_face_from_bytes(img_bytes)
            if enc is None:
                return jsonify({"error": f"No face detected in image {idx}"}), 422
            encodings.append(enc)

        student = Student(
            student_id=data["student_id"],
            name=data["name"],
            email=data["email"],
            password_hash=hash_password(data["password"]),
        )
        db.session.add(student)
        db.session.flush()  # get student.id before commit

        for enc in encodings:
            db.session.add(FaceData(student_id=student.id, face_encoding=encoding_to_bytes(enc)))

        db.session.commit()
        logger.info("Registered student %s", student.student_id)

        # Optional: create Moodle account
        moodle_user_id = get_or_create_moodle_user(student.email, student.name, student.student_id)
        if moodle_user_id:
            logger.info("Moodle user created/found: %s", moodle_user_id)

        token = generate_token(student.id, student.student_id)
        return jsonify({"message": "Registration successful", "token": token, "student": student.to_dict()}), 201

    @app.post("/api/auth/login")
    @limiter.limit("5 per 15 minutes")
    def login():
        data = request.get_json(silent=True) or {}
        ip = request.remote_addr

        # ── Face login ────────────────────────────────────────────────────────
        if data.get("face_image"):
            try:
                img_bytes = base64.b64decode(data["face_image"])
            except Exception:
                return jsonify({"error": "Invalid base64 image"}), 400

            candidate_enc = encode_face_from_bytes(img_bytes)
            if candidate_enc is None:
                return jsonify({"error": "No face detected in image"}), 422

            students = Student.query.all()
            best_match = None
            best_score = 1.0

            for student in students:
                for face_record in student.face_data:
                    match, distance = compare_faces(face_record.face_encoding, candidate_enc)
                    if match and distance < best_score:
                        best_score = distance
                        best_match = student

            if best_match is None:
                log = LoginLog(
                    student_id=None,
                    ip_address=ip,
                    status="failed",
                    face_match_score=None,
                )
                # student_id is NOT NULL in schema — skip logging anonymous failures
                return jsonify({"error": "Face not recognised"}), 401

            log = LoginLog(
                student_id=best_match.id,
                ip_address=ip,
                face_match_score=best_score,
                status="success",
            )
            db.session.add(log)
            db.session.commit()

            token = generate_token(best_match.id, best_match.student_id)
            return jsonify({"message": "Login successful", "token": token, "student": best_match.to_dict()}), 200

        # ── Password fallback ─────────────────────────────────────────────────
        if data.get("student_id") and data.get("password"):
            student = Student.query.filter_by(student_id=data["student_id"]).first()
            if not student or not verify_password(data["password"], student.password_hash):
                return jsonify({"error": "Invalid credentials"}), 401

            log = LoginLog(student_id=student.id, ip_address=ip, status="password")
            db.session.add(log)
            db.session.commit()

            token = generate_token(student.id, student.student_id)
            return jsonify({"message": "Login successful", "token": token, "student": student.to_dict()}), 200

        return jsonify({"error": "Provide face_image or student_id + password"}), 400

    @app.post("/api/auth/logout")
    @jwt_required()
    def logout():
        student_db_id = get_current_student_id()
        if student_db_id:
            log = (
                LoginLog.query.filter_by(student_id=student_db_id, logout_time=None)
                .order_by(LoginLog.login_time.desc())
                .first()
            )
            if log:
                log.logout_time = datetime.now(timezone.utc)
                db.session.commit()
        return jsonify({"message": "Logged out successfully"}), 200

    # ════════════════════════════════════════════════════════════════════════
    # Student endpoints
    # ════════════════════════════════════════════════════════════════════════

    @app.get("/api/student/profile")
    @jwt_required()
    def get_profile():
        student_db_id = get_current_student_id()
        student, err = _student_or_404(student_db_id)
        if err:
            return err
        return jsonify({"student": student.to_dict()}), 200

    @app.post("/api/student/update-face")
    @jwt_required()
    @limiter.limit("10 per hour")
    def update_face():
        student_db_id = get_current_student_id()
        student, err = _student_or_404(student_db_id)
        if err:
            return err

        data = request.get_json(silent=True) or {}
        face_images = data.get("face_images", [])
        if not isinstance(face_images, list) or not (1 <= len(face_images) <= 10):
            return jsonify({"error": "Provide between 1 and 10 face images"}), 400

        new_encodings = []
        for idx, img_b64 in enumerate(face_images):
            try:
                img_bytes = base64.b64decode(img_b64)
            except Exception:
                return jsonify({"error": f"Invalid base64 for image {idx}"}), 400

            enc = encode_face_from_bytes(img_bytes)
            if enc is None:
                return jsonify({"error": f"No face detected in image {idx}"}), 422
            new_encodings.append(enc)

        FaceData.query.filter_by(student_id=student.id).delete()
        for enc in new_encodings:
            db.session.add(FaceData(student_id=student.id, face_encoding=encoding_to_bytes(enc)))

        db.session.commit()
        return jsonify({"message": "Face data updated successfully"}), 200

    @app.get("/api/student/login-history")
    @jwt_required()
    def login_history():
        student_db_id = get_current_student_id()
        student, err = _student_or_404(student_db_id)
        if err:
            return err

        logs = (
            LoginLog.query.filter_by(student_id=student.id)
            .order_by(LoginLog.login_time.desc())
            .limit(50)
            .all()
        )
        return jsonify({"history": [log.to_dict() for log in logs]}), 200

    # ════════════════════════════════════════════════════════════════════════
    # Moodle OAuth endpoints
    # ════════════════════════════════════════════════════════════════════════

    @app.get("/api/moodle/login-url")
    @jwt_required()
    def moodle_login_url():
        student_db_id = get_current_student_id()
        student, err = _student_or_404(student_db_id)
        if err:
            return err

        moodle_session = (
            MoodleSession.query.filter_by(student_id=student.id)
            .order_by(MoodleSession.created_at.desc())
            .first()
        )
        moodle_user_id = moodle_session.moodle_user_id if moodle_session else None

        if not moodle_user_id:
            moodle_user_id = get_or_create_moodle_user(student.email, student.name, student.student_id)

        if not moodle_user_id:
            return jsonify({"error": "Moodle integration not configured"}), 503

        result = create_moodle_session_token(moodle_user_id)
        if not result:
            return jsonify({"error": "Failed to create Moodle session"}), 503

        session = MoodleSession(
            student_id=student.id,
            moodle_user_id=moodle_user_id,
            session_token=result["login_url"],
            expires_at=result["expires_at"],
        )
        db.session.add(session)
        db.session.commit()

        return jsonify({"login_url": result["login_url"]}), 200

    # ── Health check ──────────────────────────────────────────────────────────

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # ── Error handlers ────────────────────────────────────────────────────────
    @app.errorhandler(429)
    def rate_limit_handler(e):
        return jsonify({"error": "Too many requests. Please try again later."}), 429

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Internal server error")
        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
