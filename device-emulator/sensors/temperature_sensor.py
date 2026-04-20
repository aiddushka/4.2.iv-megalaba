import time
import random
import os
import json
import paho.mqtt.client as mqtt

from runtime_token import DeviceTokenHolder

DEVICE_UID = os.getenv("DEVICE_UID", "temp_sensor_1")
_token_holder = DeviceTokenHolder(DEVICE_UID, os.getenv("DEVICE_TOKEN", ""))
SEND_INTERVAL_SECONDS = 2
NATURAL_DRIFT = 0.15
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "").strip()
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "").strip()
MQTT_TOPIC = f"greenhouse/sensors/{DEVICE_UID}/data"
HEARTBEAT_TOPIC = f"greenhouse/devices/{DEVICE_UID}/heartbeat"
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "10"))


temp = 25.0
mqtt_client = mqtt.Client(client_id=f"{DEVICE_UID}-publisher")
if MQTT_USERNAME and MQTT_PASSWORD:
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
mqtt_client.loop_start()
last_heartbeat_at = 0.0

while True:
    now = time.time()
    if now - last_heartbeat_at >= HEARTBEAT_INTERVAL_SECONDS:
        heartbeat_payload = {
            "device_uid": DEVICE_UID,
            "device_type": "TEMP_SENSOR",
            "status": "alive",
            "device_token": _token_holder.current(),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        mqtt_client.publish(HEARTBEAT_TOPIC, json.dumps(heartbeat_payload), qos=0)
        last_heartbeat_at = now
    temp = max(10.0, min(45.0, temp + random.uniform(-NATURAL_DRIFT, NATURAL_DRIFT)))
    payload = {
        "device_uid": DEVICE_UID,
        "device_token": _token_holder.current(),
        "value": round(temp, 2),
        "sensor_type": "temperature",
    }
    try:
        mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
        print(f"Published: {payload['value']}°C Topic: {MQTT_TOPIC}")
    except Exception as e:
        print("Error:", e)
    time.sleep(SEND_INTERVAL_SECONDS)