import json
import os
from typing import Any

import paho.mqtt.client as mqtt

from app.database.session import SessionLocal
from app.schemas.sensor_schema import SensorDataCreate
from app.services import sensor_service

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_SENSOR_TOPIC = os.getenv("MQTT_SENSOR_TOPIC", "greenhouse/sensors/+/data")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "greenhouse-backend")

_client: mqtt.Client | None = None


def _decode_payload(payload_raw: bytes) -> dict[str, Any] | None:
    try:
        parsed = json.loads(payload_raw.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _on_connect(client: mqtt.Client, _userdata, _flags, reason_code, _properties=None):
    if reason_code == 0:
        client.subscribe(MQTT_SENSOR_TOPIC)
        print(f"[mqtt] subscribed to '{MQTT_SENSOR_TOPIC}'")
    else:
        print(f"[mqtt] connection failed, code={reason_code}")


def _on_message(_client: mqtt.Client, _userdata, message: mqtt.MQTTMessage):
    payload_dict = _decode_payload(message.payload)
    if not payload_dict:
        return

    try:
        payload = SensorDataCreate(**payload_dict)
    except Exception:
        return

    db = SessionLocal()
    try:
        sensor_service.ingest_sensor_data(db, payload)
    except Exception as exc:
        print(f"[mqtt] failed to ingest sensor payload: {exc}")
    finally:
        db.close()


def start_mqtt_listener() -> None:
    global _client
    if _client is not None:
        return
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
    client.loop_start()
    _client = client
    print(f"[mqtt] connecting to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")


def stop_mqtt_listener() -> None:
    global _client
    if _client is None:
        return
    _client.loop_stop()
    _client.disconnect()
    _client = None
