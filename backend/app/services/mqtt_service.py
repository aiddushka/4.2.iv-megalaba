import json
import os
import ssl
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt

from app.database.session import SessionLocal
from app.services import actuator_service
from app.schemas.sensor_schema import SensorDataCreate
from app.services import sensor_service
from app.models.device import Device
from app.services import device_token_service

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_SENSOR_TOPIC = os.getenv("MQTT_SENSOR_TOPIC", "greenhouse/sensors/+/data")
MQTT_ACTUATOR_STATE_TOPIC = os.getenv(
    "MQTT_ACTUATOR_STATE_TOPIC", "greenhouse/actuators/+/state"
)
MQTT_HEARTBEAT_TOPIC = os.getenv("MQTT_HEARTBEAT_TOPIC", "greenhouse/devices/+/heartbeat")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "greenhouse-backend")
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "").strip()
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "").strip()
MQTT_TLS_ENABLED = os.getenv("MQTT_TLS_ENABLED", "false").strip().lower() == "true"
MQTT_TLS_CA_CERT = os.getenv("MQTT_TLS_CA_CERT", "").strip()
MQTT_TLS_INSECURE = os.getenv("MQTT_TLS_INSECURE", "false").strip().lower() == "true"
MQTT_TLS_CLIENT_CERT = os.getenv("MQTT_TLS_CLIENT_CERT", "").strip()
MQTT_TLS_CLIENT_KEY = os.getenv("MQTT_TLS_CLIENT_KEY", "").strip()
if not MQTT_USERNAME or not MQTT_PASSWORD:
    raise RuntimeError("Missing required environment variables: MQTT_USERNAME/MQTT_PASSWORD")
if MQTT_TLS_ENABLED and not MQTT_TLS_CA_CERT:
    raise RuntimeError("Missing required environment variable: MQTT_TLS_CA_CERT when MQTT_TLS_ENABLED=true")
if MQTT_TLS_ENABLED and (not MQTT_TLS_CLIENT_CERT or not MQTT_TLS_CLIENT_KEY):
    raise RuntimeError(
        "Missing required environment variables: MQTT_TLS_CLIENT_CERT/MQTT_TLS_CLIENT_KEY "
        "when MQTT_TLS_ENABLED=true"
    )
DEVICE_TOKEN_PEPPER = os.getenv("DEVICE_TOKEN_PEPPER", "").strip()
if not DEVICE_TOKEN_PEPPER:
    raise RuntimeError("Missing required environment variable: DEVICE_TOKEN_PEPPER")
_DEVICE_TOKEN_REJECT_LOG_INTERVAL = float(
    os.getenv("MQTT_DEVICE_TOKEN_REJECT_LOG_INTERVAL", "30")
)

_client: mqtt.Client | None = None
_heartbeats: dict[str, dict[str, Any]] = {}
_heartbeat_received_at_mono: dict[str, float] = {}
_reject_lock = threading.Lock()
_device_token_reject_totals: dict[str, int] = {"sensor": 0, "actuator": 0, "heartbeat": 0}
_device_token_reject_last_log_mono = 0.0
_runtime_lock = threading.Lock()
_mqtt_connected = False
_last_message_mono: float | None = None
_disconnect_count = 0


def get_device_token_reject_totals() -> dict[str, int]:
    with _reject_lock:
        return dict(_device_token_reject_totals)


def get_heartbeat_ages_seconds() -> dict[str, float]:
    now = time.monotonic()
    return {
        device_uid: round(max(0.0, now - seen_at), 1)
        for device_uid, seen_at in _heartbeat_received_at_mono.items()
    }


def get_runtime_stats() -> dict[str, Any]:
    with _runtime_lock:
        connected = _mqtt_connected
        last_message_mono = _last_message_mono
        disconnect_count = _disconnect_count
    age_seconds = None if last_message_mono is None else round(max(0.0, time.monotonic() - last_message_mono), 1)
    return {
        "mqtt_connected": connected,
        "last_message_age_seconds": age_seconds,
        "disconnect_count": disconnect_count,
        "invalid_token_totals": get_device_token_reject_totals(),
        "heartbeat_count": len(_heartbeats),
    }


def _record_invalid_device_token(kind: str, device_uid: str | None) -> None:
    """Count failed verification; log at most once per interval (no token values logged)."""
    global _device_token_reject_last_log_mono
    uid = device_uid or "unknown"
    with _reject_lock:
        _device_token_reject_totals[kind] = _device_token_reject_totals.get(kind, 0) + 1
        now = time.monotonic()
        if now - _device_token_reject_last_log_mono < _DEVICE_TOKEN_REJECT_LOG_INTERVAL:
            return
        _device_token_reject_last_log_mono = now
        totals = dict(_device_token_reject_totals)
    print(
        f"[mqtt] device_token verification failed: kind={kind} device_uid={uid!r} "
        f"totals_since_startup={totals}"
    )


def _decode_payload(payload_raw: bytes) -> dict[str, Any] | None:
    try:
        parsed = json.loads(payload_raw.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _on_connect(client: mqtt.Client, _userdata, _flags, reason_code, _properties=None):
    global _mqtt_connected
    if reason_code == 0:
        with _runtime_lock:
            _mqtt_connected = True
        client.subscribe(MQTT_SENSOR_TOPIC)
        client.subscribe(MQTT_ACTUATOR_STATE_TOPIC)
        client.subscribe(MQTT_HEARTBEAT_TOPIC)
        print(
            f"[mqtt] subscribed to '{MQTT_SENSOR_TOPIC}', "
            f"'{MQTT_ACTUATOR_STATE_TOPIC}', '{MQTT_HEARTBEAT_TOPIC}'"
        )
    else:
        print(f"[mqtt] connection failed, code={reason_code}")


def _on_disconnect(_client: mqtt.Client, _userdata, reason_code, _properties=None):
    global _mqtt_connected, _disconnect_count
    with _runtime_lock:
        _mqtt_connected = False
        _disconnect_count += 1
    print(f"[mqtt] disconnected, code={reason_code}")


def _handle_sensor_payload(payload_dict: dict[str, Any]) -> None:
    try:
        payload = SensorDataCreate(**payload_dict)
    except Exception:
        return

    db = SessionLocal()
    try:
        token = payload_dict.get("device_token")
        device = db.query(Device).filter(Device.device_uid == payload.device_uid).first()
        if not device_token_service.verify_device_token(device, token, DEVICE_TOKEN_PEPPER):
            _record_invalid_device_token("sensor", payload.device_uid)
            return
        if device is not None and hasattr(device, "accepts_data") and not bool(device.accepts_data):
            return
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
        token = payload_dict.get("device_token")
        device = db.query(Device).filter(Device.device_uid == device_uid).first()
        if not device_token_service.verify_device_token(device, token, DEVICE_TOKEN_PEPPER):
            _record_invalid_device_token("actuator", str(device_uid))
            return
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
    db = SessionLocal()
    try:
        token = payload_dict.get("device_token")
        device = db.query(Device).filter(Device.device_uid == device_uid).first()
        if not device_token_service.verify_device_token(device, token, DEVICE_TOKEN_PEPPER):
            _record_invalid_device_token("heartbeat", device_uid)
            return
        _heartbeats[device_uid] = payload_dict
        _heartbeat_received_at_mono[device_uid] = time.monotonic()
    finally:
        db.close()


def _on_message(_client: mqtt.Client, _userdata, message: mqtt.MQTTMessage):
    global _last_message_mono
    with _runtime_lock:
        _last_message_mono = time.monotonic()
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
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if MQTT_TLS_ENABLED:
        client.tls_set(
            ca_certs=MQTT_TLS_CA_CERT,
            certfile=MQTT_TLS_CLIENT_CERT,
            keyfile=MQTT_TLS_CLIENT_KEY,
            cert_reqs=ssl.CERT_REQUIRED,
        )
        if MQTT_TLS_INSECURE:
            client.tls_insecure_set(True)
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
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
