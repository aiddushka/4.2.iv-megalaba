import json
import os
from typing import Any

import paho.mqtt.client as mqtt

from app.database.session import SessionLocal
from app.services import actuator_service
from app.schemas.sensor_schema import SensorDataCreate
from app.services import sensor_service

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_SENSOR_TOPIC = os.getenv("MQTT_SENSOR_TOPIC", "greenhouse/sensors/+/data")
MQTT_ACTUATOR_STATE_TOPIC = os.getenv(
    "MQTT_ACTUATOR_STATE_TOPIC", "greenhouse/actuators/+/state"
)
MQTT_HEARTBEAT_TOPIC = os.getenv("MQTT_HEARTBEAT_TOPIC", "greenhouse/devices/+/heartbeat")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "greenhouse-backend")

_client: mqtt.Client | None = None
_heartbeats: dict[str, dict[str, Any]] = {}


def _decode_payload(payload_raw: bytes) -> dict[str, Any] | None:
    try:
        parsed = json.loads(payload_raw.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _on_connect(client: mqtt.Client, _userdata, _flags, reason_code, _properties=None):
    if reason_code == 0:
        client.subscribe(MQTT_SENSOR_TOPIC)
        client.subscribe(MQTT_ACTUATOR_STATE_TOPIC)
        client.subscribe(MQTT_HEARTBEAT_TOPIC)
        print(
            f"[mqtt] subscribed to '{MQTT_SENSOR_TOPIC}', "
            f"'{MQTT_ACTUATOR_STATE_TOPIC}', '{MQTT_HEARTBEAT_TOPIC}'"
        )
    else:
        print(f"[mqtt] connection failed, code={reason_code}")


def _handle_sensor_payload(payload_dict: dict[str, Any]) -> None:
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


def _handle_actuator_state(payload_dict: dict[str, Any]) -> None:
    device_uid = payload_dict.get("device_uid")
    state = payload_dict.get("state")
    actuator_type = payload_dict.get("actuator_type")
    if not device_uid or not isinstance(state, str):
        return
    db = SessionLocal()
    try:
        actuator_service.set_actuator_state(
            db=db, device_uid=device_uid, action=state, actuator_type=actuator_type
        )
    except Exception as exc:
        print(f"[mqtt] failed to sync actuator state: {exc}")
    finally:
        db.close()


def _handle_heartbeat(topic: str, payload_dict: dict[str, Any]) -> None:
    # topic: greenhouse/devices/<device_uid>/heartbeat
    parts = topic.split("/")
    if len(parts) < 4:
        return
    device_uid = parts[2]
    _heartbeats[device_uid] = payload_dict


def _on_message(_client: mqtt.Client, _userdata, message: mqtt.MQTTMessage):
    payload_dict = _decode_payload(message.payload)
    if not payload_dict:
        return
    topic = message.topic or ""
    if topic.startswith("greenhouse/sensors/") and topic.endswith("/data"):
        _handle_sensor_payload(payload_dict)
        return
    if topic.startswith("greenhouse/actuators/") and topic.endswith("/state"):
        _handle_actuator_state(payload_dict)
        return
    if topic.startswith("greenhouse/devices/") and topic.endswith("/heartbeat"):
        _handle_heartbeat(topic, payload_dict)


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


def publish_actuator_command(device_uid: str, action: str, actuator_type: str | None) -> None:
    if _client is None:
        raise RuntimeError("MQTT client is not connected")
    topic = f"greenhouse/actuators/{device_uid}/cmd"
    payload = {
        "device_uid": device_uid,
        "action": action,
    }
    if actuator_type:
        payload["actuator_type"] = actuator_type
    _client.publish(topic, json.dumps(payload), qos=1)


def get_all_heartbeats() -> dict[str, dict[str, Any]]:
    return dict(_heartbeats)
