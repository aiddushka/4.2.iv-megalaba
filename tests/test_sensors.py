from fastapi.testclient import TestClient


def test_create_and_list_sensor_data(client: TestClient):
    payload = {
        "device_uid": "temp_sensor_1",
        "value": 25.5,
        "sensor_type": "temperature",
    }
    r = client.post("/sensor-data/", json=payload)
    assert r.status_code == 200
    created = r.json()
    assert created["device_uid"] == payload["device_uid"]
    assert created["value"] == payload["value"]

    r2 = client.get("/sensor-data/")
    assert r2.status_code == 200
    items = r2.json()
    assert any(i["id"] == created["id"] for i in items)

