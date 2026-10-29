"""SQLAlchemy models.

Every record belongs to a User via a non-nullable foreign key with
ON DELETE CASCADE, so deleting a user can never leave orphaned rows.
Dates are stored as real DATE/DATETIME types, never strings.
"""
from datetime import date, datetime, timezone

from flask_login import UserMixin
from sqlalchemy import Index
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
SEVERITIES = ["Mild", "Moderate", "Severe"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(254), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    vaccinations = db.relationship(
        "Vaccination", back_populates="user", cascade="all, delete-orphan",
        passive_deletes=True,
    )
    health_profile = db.relationship(
        "HealthProfile", back_populates="user", uselist=False,
        cascade="all, delete-orphan", passive_deletes=True,
    )
    allergies = db.relationship(
        "Allergy", back_populates="user", cascade="all, delete-orphan",
        passive_deletes=True,
    )
    emergency_contacts = db.relationship(
        "EmergencyContact", back_populates="user", cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def display_name(self) -> str:
        return self.name.strip() or self.email

    def __repr__(self) -> str:  # never include email/name in repr (log safety)
        return f"<User {self.id}>"


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


class Vaccination(db.Model):
    __tablename__ = "vaccinations"
    __table_args__ = (
        Index("ix_vaccinations_user_date", "user_id", "vaccination_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vaccine_name = db.Column(db.String(120), nullable=False)
    dose_number = db.Column(db.Integer, nullable=False, default=1)
    vaccination_date = db.Column(db.Date, nullable=False)
    next_dose_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    user = db.relationship("User", back_populates="vaccinations")

    def __repr__(self) -> str:
        return f"<Vaccination {self.id}>"


class HealthProfile(db.Model):
    __tablename__ = "health_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    date_of_birth = db.Column(db.Date, nullable=True)
    blood_group = db.Column(db.String(4), nullable=True)
    health_notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    user = db.relationship("User", back_populates="health_profile")

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        years = today.year - self.date_of_birth.year
        if (today.month, today.day) < (
            self.date_of_birth.month,
            self.date_of_birth.day,
        ):
            years -= 1
        return years if years >= 0 else None


class Allergy(db.Model):
    __tablename__ = "allergies"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    allergen = db.Column(db.String(120), nullable=False)
    severity = db.Column(db.String(10), nullable=False, default="Mild")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user = db.relationship("User", back_populates="allergies")

    def __repr__(self) -> str:
        return f"<Allergy {self.id}>"


class EmergencyContact(db.Model):
    __tablename__ = "emergency_contacts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(120), nullable=False)
    relationship = db.Column(db.String(60), nullable=False)
    phone_number = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user = db.relationship("User", back_populates="emergency_contacts")

    def __repr__(self) -> str:
        return f"<EmergencyContact {self.id}>"
