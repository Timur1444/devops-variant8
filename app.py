"""Student management application for DevOps variant 8."""

import logging
import os
import re
import sys
from time import perf_counter

from flask import Flask, g, jsonify, render_template, request
from sqlalchemy import String, URL, create_engine, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    group_name: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(120), unique=True)

    def as_dict(self):
        return {key: getattr(self, key) for key in
                ("id", "full_name", "group_name", "email")}


def configured_database_url():
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if os.getenv("DB_HOST"):
        return URL.create(
            "postgresql+psycopg", username=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"], host=os.environ["DB_HOST"],
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.environ["DB_NAME"],
        )
    return "sqlite:///students.db"


def validate_student(payload):
    if not isinstance(payload, dict):
        return None, "JSON object required"
    values = {}
    for key, limit in (("full_name", 120), ("group_name", 30), ("email", 120)):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
            return None, f"Invalid {key}"
        values[key] = value.strip()
    values["email"] = values["email"].lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", values["email"]):
        return None, "Invalid email"
    return values, None


def create_app(database_url=None):
    app = Flask(__name__)
    engine = create_engine(database_url or configured_database_url(), pool_pre_ping=True)
    Base.metadata.create_all(engine)
    app.extensions["db_engine"] = engine
    app.config["APP_VERSION"] = os.getenv("APP_VERSION", "1.0.0")
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(levelname)s %(message)s")

    @app.before_request
    def begin_request():
        g.started = perf_counter()

    @app.after_request
    def log_response(response):
        elapsed_ms = (perf_counter() - g.started) * 1000
        app.logger.info("method=%s path=%s status=%s duration_ms=%.1f",
                        request.method, request.path, response.status_code, elapsed_ms)
        return response

    @app.get("/")
    def index():
        return render_template("index.html", version=app.config["APP_VERSION"])

    @app.get("/health")
    def health():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return jsonify(status="error", database="unavailable"), 503
        return jsonify(status="ok", database=engine.dialect.name,
                       version=app.config["APP_VERSION"])

    @app.get("/api/students")
    def list_students():
        with Session(engine) as session:
            return jsonify([s.as_dict() for s in session.scalars(
                select(Student).order_by(Student.id))])

    @app.get("/api/students/<int:student_id>")
    def get_student(student_id):
        with Session(engine) as session:
            student = session.get(Student, student_id)
            if student is None:
                return jsonify(error="Student not found"), 404
            return jsonify(student.as_dict())

    @app.route("/api/students", methods=["POST"])
    @app.route("/api/students/<int:student_id>", methods=["PUT"])
    def save_student(student_id=None):
        values, error = validate_student(request.get_json(silent=True))
        if error:
            return jsonify(error=error), 400
        with Session(engine) as session:
            student = session.get(Student, student_id) if student_id else Student()
            if student is None:
                return jsonify(error="Student not found"), 404
            for key, value in values.items():
                setattr(student, key, value)
            session.add(student)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return jsonify(error="Email already exists"), 409
            return jsonify(student.as_dict()), 200 if student_id else 201

    @app.delete("/api/students/<int:student_id>")
    def delete_student(student_id):
        with Session(engine) as session:
            student = session.get(Student, student_id)
            if student is None:
                return jsonify(error="Student not found"), 404
            session.delete(student)
            session.commit()
            return "", 204

    return app
