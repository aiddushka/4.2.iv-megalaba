import json
import os
import ssl
import time

import paho.mqtt.client as mqtt

from runtime_token import DeviceTokenHolder

DEVICE_UID = os.getenv("DEVICE_UID", "actuator_1")
_token_holder = DeviceTokenHolder(DEVICE_UID, os.getenv("DEVICE_TOKEN", ""))
ACTUATOR_TYPE = os.getenv("ACTUATOR_TYPE", "UNKNOWN_ACTUATOR")
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TLS_ENABLED = os.getenv("MQTT_TLS_ENABLED", "false").strip().lower() == "true"
MQTT_TLS_CA_CERT = os.getenv("MQTT_TLS_CA_CERT", "").strip()
MQTT_TLS_INSECURE = os.getenv("MQTT_TLS_INSECURE", "false").strip().lower() == "true"
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "").strip()
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "").strip()
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "10"))

CMD_TOPIC = f"greenhouse/actuators/{DEVICE_UID}/cmd"
STATE_TOPIC = f"greenhouse/actuators/{DEVICE_UID}/state"
HEARTBEAT_TOPIC = f"greenhouse/devices/{DEVICE_UID}/heartbeat"


def run_actuator_listener(default_state: str = "OFF") -> None:
    current_state = (default_state or "OFF").upper()
    last_heartbeat_at = 0.0

    client = mqtt.Client(client_id=f"{DEVICE_UID}-actuator")
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if MQTT_TLS_ENABLED:
        client.tls_set(ca_certs=MQTT_TLS_CA_CERT, cert_reqs=ssl.CERT_REQUIRED)
        if MQTT_TLS_INSECURE:
            client.tls_insecure_set(True)

    def on_connect(mqtt_client: mqtt.Client, _userdata, _flags, reason_code, _properties=None):
        if reason_code == 0:
            mqtt_client.subscribe(CMD_TOPIC)
            print(f"[{DEVICE_UID}] subscribed to {CMD_TOPIC}")
        else:
            print(f"[{DEVICE_UID}] mqtt connect failed: code={reason_code}")

    def on_message(mqtt_client: mqtt.Client, _userdata, message: mqtt.MQTTMessage):
        nonlocal current_state
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except Exception:
            return
        action = str(payload.get("action", "")).upper()
        if action not in {"ON", "OFF"}:
            return
        current_state = action
        state_payload = {
            "device_uid": DEVICE_UID,
            "device_token": _token_holder.current(),
            "actuator_type": ACTUATOR_TYPE,
            "state": current_state,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        mqtt_client.publish(STATE_TOPIC, json.dumps(state_payload), qos=1)
        print(f"[{DEVICE_UID}] command applied: {current_state}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
    client.loop_start()

    while True:
        now = time.time()
        if now - last_heartbeat_at >= HEARTBEAT_INTERVAL_SECONDS:
            heartbeat_payload = {
                "device_uid": DEVICE_UID,
                "device_token": _token_holder.current(),
                "device_type": ACTUATOR_TYPE,
                "status": "alive",
                "state": current_state,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            client.publish(HEARTBEAT_TOPIC, json.dumps(heartbeat_payload), qos=0)
            last_heartbeat_at = now
        time.sleep(1)
