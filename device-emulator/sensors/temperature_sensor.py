import time
import random
import os
import json
import requests
import paho.mqtt.client as mqtt

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
STATUS_URL = f"{BACKEND_URL}/devices/status/{{device_uid}}"
DEVICE_UID = os.getenv("DEVICE_UID", "temp_sensor_1")
SEND_INTERVAL_SECONDS = 2
NATURAL_DRIFT = 0.15
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = f"greenhouse/sensors/{DEVICE_UID}/data"


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
mqtt_client = mqtt.Client(client_id=f"{DEVICE_UID}-publisher")
mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
mqtt_client.loop_start()

while True:
    if not is_device_active(DEVICE_UID):
        print(f"{DEVICE_UID}: waiting for admin activation...")
        time.sleep(SEND_INTERVAL_SECONDS)
        continue
    temp = max(10.0, min(45.0, temp + random.uniform(-NATURAL_DRIFT, NATURAL_DRIFT)))
    payload = {"device_uid": DEVICE_UID, "value": round(temp, 2), "sensor_type": "temperature"}
    try:
        mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
        print(f"Published: {payload['value']}°C Topic: {MQTT_TOPIC}")
    except Exception as e:
        print("Error:", e)
    time.sleep(SEND_INTERVAL_SECONDS)