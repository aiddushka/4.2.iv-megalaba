import time
import random
import requests

API_URL = "http://localhost:8000/sensor-data/"
DEVICE_UID = "temp_sensor_1"

while True:
    temp = round(20 + random.random() * 10, 2)
    payload = {"device_uid": DEVICE_UID, "value": temp}
    try:
        r = requests.post(API_URL, json=payload)
        print(f"Sent: {temp}°C Status: {r.status_code}")
    except Exception as e:
        print("Error:", e)
    time.sleep(5)