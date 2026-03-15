import time
import random
import requests

API_URL = "http://localhost:8000/sensor-data/"
DEVICE_UID = "humidity_air_sensor_1"

if __name__ == "__main__":
    while True:
        humidity = round(40 + random.random() * 40, 2)  # 40–80 %RH
        payload = {"device_uid": DEVICE_UID, "value": humidity}
        try:
            r = requests.post(API_URL, json=payload, timeout=5)
            print(f"Sent air humidity: {humidity}% Status: {r.status_code}")
        except Exception as e:
            print("Error sending air humidity:", e)
        time.sleep(5)

