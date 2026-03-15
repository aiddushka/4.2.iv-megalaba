import time
import random
import requests

API_URL = "http://localhost:8000/sensor-data/"
DEVICE_UID = "light_sensor_1"

if __name__ == "__main__":
    while True:
        # Условный уровень освещённости, люксы
        light_level = round(100 + random.random() * 900, 2)  # 100–1000 lx
        payload = {"device_uid": DEVICE_UID, "value": light_level}
        try:
            r = requests.post(API_URL, json=payload, timeout=5)
            print(f"Sent light level: {light_level} lx Status: {r.status_code}")
        except Exception as e:
            print("Error sending light level:", e)
        time.sleep(5)

