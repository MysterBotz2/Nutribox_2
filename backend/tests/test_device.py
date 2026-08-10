from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_simulate_device_returns_valid_reading() -> None:
    response = client.post(
        "/api/device/simulate",
        json={"weight_grams": 180, "temperature_celsius": 35.5},
    )

    assert response.status_code == 200
    assert response.json() == {
        "weight_grams": 180.0,
        "temperature_celsius": 35.5,
        "source": "simulated",
    }


def test_simulate_device_accepts_zero_weight() -> None:
    response = client.post(
        "/api/device/simulate",
        json={"weight_grams": 0, "temperature_celsius": 20},
    )

    assert response.status_code == 200
    assert response.json()["weight_grams"] == 0.0


def test_simulate_device_accepts_maximum_weight() -> None:
    response = client.post(
        "/api/device/simulate",
        json={"weight_grams": 5000, "temperature_celsius": 20},
    )

    assert response.status_code == 200
    assert response.json()["weight_grams"] == 5000.0


def test_simulate_device_rejects_invalid_weights() -> None:
    for weight_grams in (-0.1, 5000.1, "not-a-number"):
        response = client.post(
            "/api/device/simulate",
            json={"weight_grams": weight_grams, "temperature_celsius": 20},
        )

        assert response.status_code == 422


def test_simulate_device_rejects_non_finite_values() -> None:
    for invalid_number in ("NaN", "Infinity", "-Infinity"):
        response = client.post(
            "/api/device/simulate",
            content=(
                '{"weight_grams": '
                f"{invalid_number}"
                ', "temperature_celsius": 20}'
            ),
            headers={"content-type": "application/json"},
        )

        assert response.status_code == 422


def test_simulate_device_rejects_invalid_temperature() -> None:
    response = client.post(
        "/api/device/simulate",
        json={"weight_grams": 180, "temperature_celsius": "not-a-number"},
    )

    assert response.status_code == 422
