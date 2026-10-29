"""WTForms definitions with server-side validation."""
import re
from datetime import date

from flask_wtf import FlaskForm
from wtforms import (DateField, PasswordField, SelectField, StringField,
                     SubmitField, TextAreaField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length,
                                NumberRange, Optional, ValidationError)

from .extensions import db
from .models import BLOOD_GROUPS, SEVERITIES, User


class RegistrationForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(2, 80)],
                       render_kw={"placeholder": "e.g. Priya Sharma", "autocomplete": "name"})
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=254)],
                        render_kw={"placeholder": "you@example.com", "autocomplete": "email"})
    password = PasswordField("Password", validators=[
        DataRequired(),
        Length(min=8, max=128, message="Password must be at least 8 characters."),
    ], render_kw={"placeholder": "At least 8 characters", "autocomplete": "new-password"})
    confirm_password = PasswordField("Confirm password", validators=[
        DataRequired(),
        EqualTo("password", message="Passwords do not match."),
    ], render_kw={"placeholder": "Repeat your password", "autocomplete": "new-password"})
    submit = SubmitField("Create account")

    def validate_email(self, field):
        existing = db.session.execute(
            db.select(User).where(db.func.lower(User.email) == field.data.strip().lower())
        ).scalar_one_or_none()
        if existing:
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email address", validators=[DataRequired(), Email()],
                        render_kw={"placeholder": "you@example.com", "autocomplete": "email"})
    password = PasswordField("Password", validators=[DataRequired()],
                             render_kw={"placeholder": "Your password", "autocomplete": "current-password"})
    submit = SubmitField("Sign in")


class VaccinationForm(FlaskForm):
    vaccine_name = StringField("Vaccine name", validators=[DataRequired(), Length(2, 120)],
                               render_kw={"placeholder": "e.g. Hepatitis B"})
    dose_number = SelectField("Dose number", choices=[(str(i), f"Dose {i}") for i in range(1, 11)],
                              coerce=str, validators=[DataRequired()])
    vaccination_date = DateField("Date administered", validators=[DataRequired()],
                                 render_kw={"type": "date"})
    next_dose_date = DateField("Next dose due (optional)", validators=[Optional()],
                               render_kw={"type": "date"})
    notes = TextAreaField("Notes (optional)", validators=[Optional(), Length(max=2000)],
                          render_kw={"rows": 3, "placeholder": "Clinic, batch number, side effects..."})
    submit = SubmitField("Save record")

    def validate_vaccination_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError("Date administered cannot be in the future.")

    def validate_next_dose_date(self, field):
        if field.data and self.vaccination_date.data and field.data <= self.vaccination_date.data:
            raise ValidationError("Next dose date must be after the date administered.")


class HealthProfileForm(FlaskForm):
    date_of_birth = DateField("Date of birth (optional)", validators=[Optional()],
                              render_kw={"type": "date"})
    blood_group = SelectField("Blood group (optional)",
                              choices=[("", "Prefer not to say")] + [(g, g) for g in BLOOD_GROUPS],
                              validators=[Optional()])
    health_notes = TextAreaField("Basic health notes (optional)",
                                 validators=[Optional(), Length(max=2000)],
                                 render_kw={"rows": 4, "placeholder": "Chronic conditions, medications, anything useful in an emergency..."})
    submit = SubmitField("Save profile")

    def validate_date_of_birth(self, field):
        if field.data and field.data >= date.today():
            raise ValidationError("Date of birth must be in the past.")

    def validate_blood_group(self, field):
        if field.data and field.data not in BLOOD_GROUPS:
            raise ValidationError("Please choose a valid blood group.")


class AllergyForm(FlaskForm):
    allergen = StringField("Allergen", validators=[DataRequired(), Length(2, 120)],
                           render_kw={"placeholder": "e.g. Penicillin"})
    severity = SelectField("Severity", choices=[(s, s) for s in SEVERITIES],
                           validators=[DataRequired()])
    notes = TextAreaField("Notes (optional)", validators=[Optional(), Length(max=1000)],
                          render_kw={"rows": 3, "placeholder": "Reaction details, treatments..."})
    submit = SubmitField("Save allergy")

    def validate_severity(self, field):
        if field.data not in SEVERITIES:
            raise ValidationError("Please choose a valid severity.")


class EmergencyContactForm(FlaskForm):
    name = StringField("Contact name", validators=[DataRequired(), Length(2, 120)],
                       render_kw={"placeholder": "e.g. Arun Kumar"})
    relationship = StringField("Relationship", validators=[DataRequired(), Length(2, 60)],
                               render_kw={"placeholder": "e.g. Spouse, Parent, Friend"})
    phone_number = StringField("Phone number", validators=[DataRequired(), Length(5, 32)],
                               render_kw={"placeholder": "+91 98765 43210", "autocomplete": "tel"})
    submit = SubmitField("Save contact")

    _PHONE_RE = re.compile(r"^\+?[\d(][0-9\s\-().]{3,31}[\d)]$")

    def validate_phone_number(self, field):
        # Deliberately lenient: formats differ by country. We only require
        # digits (optionally with +, spaces, dashes, parentheses) and a
        # sensible length, with at least 5 digits.
        value = field.data.strip()
        if not self._PHONE_RE.match(value):
            raise ValidationError("Enter a valid phone number (digits, spaces, dashes, parentheses, optional leading +).")
        if sum(c.isdigit() for c in value) < 5:
            raise ValidationError("Phone number must contain at least 5 digits.")


class DeleteAccountForm(FlaskForm):
    password = PasswordField("Confirm your password", validators=[DataRequired()],
                             render_kw={"autocomplete": "current-password"})
    submit = SubmitField("Permanently delete my account and data")
