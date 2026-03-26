import hmac
import json
from hashlib import sha256
from typing import Any


def sign_hmac_hex(device_secret: str, base_str: str) -> str:
    return hmac.new(
        device_secret.encode("utf-8"), base_str.encode("utf-8"), sha256
    ).hexdigest()


def telemetry_base_str(
    device_uid: str, sensor_type: str, value: float, ts: int, nonce: str
) -> str:
    return f"telemetry|{device_uid}|{sensor_type}|{value}|{ts}|{nonce}"


def status_base_str(
    device_uid: str, actuator_type: str, state: str, ts: int, nonce: str
) -> str:
    return f"status|{device_uid}|{actuator_type}|{state}|{ts}|{nonce}"


def command_base_str(
    device_uid: str, actuator_type: str, action: str, ts: int, nonce: str
) -> str:
    return f"commands|{device_uid}|{action}|{actuator_type}|{ts}|{nonce}"


def mqtt_topic(base_topic: str, device_uid: str, suffix: str) -> str:
    base_topic = base_topic.strip("/")
    return f"{base_topic}/{device_uid}/{suffix}"


def to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)

