import time
import requests

DEVICE_UID = "ventilation_1"
API_URL = "http://localhost:8000/actuators/control/"

if __name__ == "__main__":
    while True:
        # Простой цикл: включаем и выключаем каждые 10 секунд
        for action in ["ON", "OFF"]:
            payload = {"device_uid": DEVICE_UID, "action": action}
            try:
                r = requests.post(API_URL, json=payload, timeout=5)
                print(f"{DEVICE_UID} -> {action} Status: {r.status_code}")
            except Exception as e:
                print("Error controlling ventilation:", e)
            time.sleep(10)

