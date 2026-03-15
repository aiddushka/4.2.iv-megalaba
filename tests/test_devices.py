from fastapi.testclient import TestClient


def test_register_and_get_unassigned(client: TestClient):
    # регистрируем устройство
    payload = {
        "device_uid": "test_device_1",
        "device_type": "CONTROLLER",
        "description": "Тестовое устройство",
        "location_hint": "Тестовая локация",
    }
    r = client.post("/devices/register", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["device_uid"] == payload["device_uid"]
    assert data["status"] == "unassigned"

    # проверяем, что оно попало в список unassigned
    r2 = client.get("/devices/unassigned")
    assert r2.status_code == 200
    devices = r2.json()
    assert any(d["device_uid"] == payload["device_uid"] for d in devices)

