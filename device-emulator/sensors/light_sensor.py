import time
import random
import os
import json
import paho.mqtt.client as mqtt

DEVICE_UID = os.getenv("DEVICE_UID", "light_sensor_1")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "")
SEND_INTERVAL_SECONDS = 2
NATURAL_DRIFT = 4.0
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = f"greenhouse/sensors/{DEVICE_UID}/data"
HEARTBEAT_TOPIC = f"greenhouse/devices/{DEVICE_UID}/heartbeat"
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "10"))


if __name__ == "__main__":
    light_level = 400.0
    mqtt_client = mqtt.Client(client_id=f"{DEVICE_UID}-publisher")
    mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
    mqtt_client.loop_start()
    last_heartbeat_at = 0.0
    while True:
        now = time.time()
        if now - last_heartbeat_at >= HEARTBEAT_INTERVAL_SECONDS:
            heartbeat_payload = {
                "device_uid": DEVICE_UID,
                "device_type": "LIGHT_SENSOR",
                "status": "alive",
                "device_token": DEVICE_TOKEN,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            mqtt_client.publish(HEARTBEAT_TOPIC, json.dumps(heartbeat_payload), qos=0)
            last_heartbeat_at = now
        # Условный уровень освещённости, люксы
        light_level = max(10.0, min(1200.0, light_level + random.uniform(-NATURAL_DRIFT, NATURAL_DRIFT)))
        payload = {
            "device_uid": DEVICE_UID,
            "device_token": DEVICE_TOKEN,
            "value": round(light_level, 2),
            "sensor_type": "light",
        }
        try:
            mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
            print(f"Published light level: {payload['value']} lx Topic: {MQTT_TOPIC}")
        except Exception as e:
            print("Error sending light level:", e)
        time.sleep(SEND_INTERVAL_SECONDS)

