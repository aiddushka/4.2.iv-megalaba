import time
import random
import os
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_URL = f"{BACKEND_URL}/sensor-data/"
STATUS_URL = f"{BACKEND_URL}/devices/status/{{device_uid}}"
DEVICE_UID = os.getenv("DEVICE_UID", "temp_sensor_1")
SEND_INTERVAL_SECONDS = 2
NATURAL_DRIFT = 0.15


def is_device_active(device_uid: str) -> bool:
    try:
        response = requests.get(STATUS_URL.format(device_uid=device_uid), timeout=5)
        if response.status_code != 200:
            return False
        payload = response.json()
        return payload.get("status") == "active"
    except Exception:
        return False


temp = 25.0
while True:
    if not is_device_active(DEVICE_UID):
        print(f"{DEVICE_UID}: waiting for admin activation...")
        time.sleep(SEND_INTERVAL_SECONDS)
        continue
    temp = max(10.0, min(45.0, temp + random.uniform(-NATURAL_DRIFT, NATURAL_DRIFT)))
    payload = {"device_uid": DEVICE_UID, "value": round(temp, 2), "sensor_type": "temperature"}
    try:
        r = requests.post(API_URL, json=payload, timeout=5)
        print(f"Sent: {payload['value']}°C Status: {r.status_code}")
    except Exception as e:
        print("Error:", e)
    time.sleep(SEND_INTERVAL_SECONDS)