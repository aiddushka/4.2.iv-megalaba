import time
import random
import os
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_URL = f"{BACKEND_URL}/sensor-data/"
STATUS_URL = f"{BACKEND_URL}/devices/status/{{device_uid}}"
DEVICE_UID = os.getenv("DEVICE_UID", "light_sensor_1")
SEND_INTERVAL_SECONDS = 2
NATURAL_DRIFT = 4.0


def is_device_active(device_uid: str) -> bool:
    try:
        response = requests.get(STATUS_URL.format(device_uid=device_uid), timeout=5)
        if response.status_code != 200:
            return False
        payload = response.json()
        return payload.get("status") == "active"
    except Exception:
        return False


if __name__ == "__main__":
    light_level = 400.0
    while True:
        if not is_device_active(DEVICE_UID):
            print(f"{DEVICE_UID}: waiting for admin activation...")
            time.sleep(SEND_INTERVAL_SECONDS)
            continue
        # Условный уровень освещённости, люксы
        light_level = max(10.0, min(1200.0, light_level + random.uniform(-NATURAL_DRIFT, NATURAL_DRIFT)))
        payload = {"device_uid": DEVICE_UID, "value": round(light_level, 2), "sensor_type": "light"}
        try:
            r = requests.post(API_URL, json=payload, timeout=5)
            print(f"Sent light level: {payload['value']} lx Status: {r.status_code}")
        except Exception as e:
            print("Error sending light level:", e)
        time.sleep(SEND_INTERVAL_SECONDS)

