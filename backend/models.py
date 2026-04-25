from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy


def _now():
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)

db = SQLAlchemy()


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    face_data = db.relationship("FaceData", backref="student", lazy=True, cascade="all, delete-orphan")
    login_logs = db.relationship("LoginLog", backref="student", lazy=True, cascade="all, delete-orphan")
    moodle_sessions = db.relationship("MoodleSession", backref="student", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class FaceData(db.Model):
    __tablename__ = "face_data"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    face_encoding = db.Column(db.LargeBinary, nullable=False)
    captured_at = db.Column(db.DateTime, default=_now)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "captured_at": self.captured_at.isoformat(),
        }


class LoginLog(db.Model):
    __tablename__ = "login_logs"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    login_time = db.Column(db.DateTime, default=_now)
    logout_time = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    face_match_score = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="success")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "login_time": self.login_time.isoformat(),
            "logout_time": self.logout_time.isoformat() if self.logout_time else None,
            "ip_address": self.ip_address,
            "face_match_score": self.face_match_score,
            "status": self.status,
        }


class MoodleSession(db.Model):
    __tablename__ = "moodle_sessions"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    moodle_user_id = db.Column(db.String(100), nullable=True)
    session_token = db.Column(db.String(500), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=_now)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "moodle_user_id": self.moodle_user_id,
            "session_token": self.session_token,
            "expires_at": self.expires_at.isoformat(),
        }
