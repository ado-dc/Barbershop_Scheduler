from app import APPOINTMENTS, TOKENS, app


def _login(client, username, password):
    response = client.post("/login", json={"username": username, "password": password})
    return response.get_json()["token"]


def setup_function():
    APPOINTMENTS.clear()
    TOKENS.clear()


def test_login_and_list_slots():
    client = app.test_client()

    token = _login(client, "cliente1", "123456")
    response = client.get("/slots", headers={"Authorization": token})

    assert response.status_code == 200
    body = response.get_json()
    assert "09:00" in body["available_slots"]


def test_customer_can_book_appointment():
    client = app.test_client()
    token = _login(client, "cliente1", "123456")

    response = client.post(
        "/appointments",
        headers={"Authorization": token},
        json={"slot": "10:00"},
    )

    assert response.status_code == 201
    assert response.get_json()["slot"] == "10:00"

    slots_response = client.get("/slots", headers={"Authorization": token})
    assert "10:00" not in slots_response.get_json()["available_slots"]


def test_barber_can_manage_appointment():
    client = app.test_client()
    customer_token = _login(client, "cliente1", "123456")
    barber_token = _login(client, "barbeiro1", "123456")

    created = client.post(
        "/appointments",
        headers={"Authorization": customer_token},
        json={"slot": "11:00"},
    )

    appointment_id = created.get_json()["id"]

    update = client.patch(
        f"/appointments/{appointment_id}",
        headers={"Authorization": barber_token},
        json={"status": "completed"},
    )

    assert update.status_code == 200
    assert update.get_json()["status"] == "completed"


def test_customer_cannot_manage_appointment():
    client = app.test_client()
    customer_token = _login(client, "cliente1", "123456")

    response = client.patch(
        "/appointments/1",
        headers={"Authorization": customer_token},
        json={"status": "cancelled"},
    )

    assert response.status_code == 403
