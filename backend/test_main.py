
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Each test gets its own temporary database.
    # The real mini_noc.db is not modified.
    test_database = tmp_path / "test_noc.db"

    monkeypatch.setattr(
        main,
        "DATABASE",
        test_database
    )

    main.initialize_database()

    with TestClient(main.app) as test_client:
        yield test_client


def test_initial_devices(client):
    response = client.get("/api/devices")

    assert response.status_code == 200

    devices = response.json()

    assert len(devices) == 5
    assert devices[0]["name"] == "Core Router"
    assert devices[3]["name"] == "Encoder 01"


def test_initial_summary(client):
    response = client.get("/api/summary")

    assert response.status_code == 200

    summary = response.json()

    assert summary["total"] == 5
    assert summary["online"] == 4
    assert summary["offline"] == 1


def test_initial_encoder_incident(client):
    response = client.get("/api/incidents")

    assert response.status_code == 200

    incidents = response.json()

    assert len(incidents) == 1
    assert incidents[0]["device_name"] == "Encoder 01"
    assert incidents[0]["severity"] == "P2"
    assert incidents[0]["status"] == "open"


def test_incident_workflow(client):
    # Simulate Core Router going offline
    response = client.post(
        "/api/devices/1/toggle"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "offline"

    # Verify that a P1 incident was created
    incidents = client.get(
        "/api/incidents"
    ).json()

    router_incident = next(
        incident for incident in incidents
        if incident["device_id"] == 1
    )

    assert router_incident["severity"] == "P1"
    assert router_incident["status"] == "open"

    incident_id = router_incident["id"]

    # Acknowledge incident
    response = client.post(
        f"/api/incidents/{incident_id}/acknowledge"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"

    # Resolution should fail while device is offline
    response = client.post(
        f"/api/incidents/{incident_id}/resolve"
    )

    assert response.status_code == 409

    # Recover Core Router
    response = client.post(
        "/api/devices/1/toggle"
    )

    assert response.json()["status"] == "online"

    # Resolve the incident
    response = client.post(
        f"/api/incidents/{incident_id}/resolve"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


def test_invalid_device(client):
    response = client.post(
        "/api/devices/999/toggle"
    )

    assert response.status_code == 404


def test_invalid_incident(client):
    response = client.post(
        "/api/incidents/999/acknowledge"
    )

    assert response.status_code == 404


def test_database_persistence(client):
    # Make Switch 01 offline
    client.post("/api/devices/2/toggle")

    # Simulate database initialization again
    main.initialize_database()

    # Data must still exist
    devices = client.get("/api/devices").json()

    switch = next(
        device for device in devices
        if device["id"] == 2
    )

    assert switch["status"] == "offline"
