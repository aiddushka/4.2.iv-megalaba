import time
import random
import requests

API_URL = "http://localhost:8000/sensor-data/"
DEVICE_UID = "humidity_soil_sensor_1"

if __name__ == "__main__":
    while True:
        soil_moisture = round(20 + random.random() * 60, 2)  # 20–80 %
        payload = {"device_uid": DEVICE_UID, "value": soil_moisture}
        try:
            r = requests.post(API_URL, json=payload, timeout=5)
            print(f"Sent soil moisture: {soil_moisture}% Status: {r.status_code}")
        except Exception as e:
            print("Error sending soil moisture:", e)
        time.sleep(5)

