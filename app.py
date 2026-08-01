from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Any
from uuid import uuid4

from flask import Flask, g, jsonify, request

app = Flask(__name__)

USERS = {
    "cliente1": {"password": "123456", "role": "customer"},
    "barbeiro1": {"password": "123456", "role": "barber"},
}

TIME_SLOTS = [
    "09:00",
    "10:00",
    "11:00",
    "13:00",
    "14:00",
    "15:00",
    "16:00",
]

TOKENS: dict[str, dict[str, str]] = {}


@dataclass
class Appointment:
    id: int
    customer: str
    slot: str
    status: str = "scheduled"


APPOINTMENTS: list[Appointment] = []


def _extract_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "", 1).strip()
    return auth_header.strip() or None


def require_auth(roles: set[str] | None = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            token = _extract_token()
            user = TOKENS.get(token or "")
            if not user:
                return jsonify({"error": "Unauthorized"}), 401
            if roles and user["role"] not in roles:
                return jsonify({"error": "Forbidden"}), 403
            g.user = user
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _available_slots() -> list[str]:
    booked_slots = {appointment.slot for appointment in APPOINTMENTS if appointment.status == "scheduled"}
    return [slot for slot in TIME_SLOTS if slot not in booked_slots]


@app.post("/login")
def login():
    data: dict[str, Any] = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    user = USERS.get(username)
    if not user or user["password"] != password:
        return jsonify({"error": "Invalid credentials"}), 401

    token = str(uuid4())
    TOKENS[token] = {"username": username, "role": user["role"]}
    return jsonify({"token": token, "role": user["role"]})


@app.get("/slots")
@require_auth({"customer", "barber"})
def list_slots():
    return jsonify({"available_slots": _available_slots()})


@app.post("/appointments")
@require_auth({"customer"})
def create_appointment():
    data: dict[str, Any] = request.get_json(silent=True) or {}
    slot = data.get("slot")

    if slot not in TIME_SLOTS:
        return jsonify({"error": "Invalid slot"}), 400

    if slot not in _available_slots():
        return jsonify({"error": "Slot unavailable"}), 409

    appointment = Appointment(
        id=len(APPOINTMENTS) + 1,
        customer=g.user["username"],
        slot=slot,
    )
    APPOINTMENTS.append(appointment)
    return jsonify(appointment.__dict__), 201


@app.get("/appointments")
@require_auth({"customer", "barber"})
def list_appointments():
    user = g.user
    if user["role"] == "barber":
        appointments = APPOINTMENTS
    else:
        appointments = [a for a in APPOINTMENTS if a.customer == user["username"]]

    return jsonify([appointment.__dict__ for appointment in appointments])


@app.patch("/appointments/<int:appointment_id>")
@require_auth({"barber"})
def manage_appointment(appointment_id: int):
    data: dict[str, Any] = request.get_json(silent=True) or {}
    status = data.get("status")
    allowed_statuses = {"scheduled", "completed", "cancelled"}

    if status not in allowed_statuses:
        return jsonify({"error": "Invalid status"}), 400

    appointment = next((a for a in APPOINTMENTS if a.id == appointment_id), None)
    if not appointment:
        return jsonify({"error": "Appointment not found"}), 404

    appointment.status = status
    return jsonify(appointment.__dict__)


if __name__ == "__main__":
    app.run()
