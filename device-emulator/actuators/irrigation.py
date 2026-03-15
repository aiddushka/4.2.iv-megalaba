import time
import requests

DEVICE_UID = "irrigation_1"
API_URL = "http://localhost:8000/actuators/control/"

while True:
    # простой пример — включаем и выключаем каждые 10 секунд
    for action in ["ON", "OFF"]:
        payload = {"device_uid": DEVICE_UID, "action": action}
        try:
            r = requests.post(API_URL, json=payload)
            print(f"{DEVICE_UID} -> {action} Status: {r.status_code}")
        except Exception as e:
            print("Error:", e)
        time.sleep(10)