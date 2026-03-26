import hmac
import json
import os
import threading
import time
import uuid
from hashlib import sha256
from typing import Any

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.device import Device
from app.services.actuator_service import set_actuator_state
from app.services.sensor_service import create_sensor_data


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


class MQTTManager:
    """
    MQTT-маршрутизатор для мегалабы:
    - устройств -> backend: telemetry и status
    - backend -> устройств: commands
    """

    def __init__(self) -> None:
        self.host = os.getenv("MQTT_HOST", "mqtt")
        self.port = _env_int("MQTT_PORT", 1883)
        self.allowed_drift_seconds = _env_int("MQTT_ALLOWED_DRIFT_SECONDS", 300)
        self.base_topic = os.getenv("MQTT_BASE_TOPIC", "greenhouse/devices").strip("/")

        # key: "<msg_type>|<device_uid>|<nonce>" => ts
        self.recent_nonces: dict[str, int] = {}
        self._nonce_lock = threading.Lock()

        self._client = mqtt.Client()
        self._client.on_message = self._on_message

        self._connected = threading.Event()

        # Подписки:
        # greenhouse/devices/<device_uid>/telemetry
        # greenhouse/devices/<device_uid>/status
        self._telemetry_topic = f"{self.base_topic}/+/telemetry"
        self._status_topic = f"{self.base_topic}/+/status"
        self._commands_topic_template = f"{self.base_topic}/{{device_uid}}/commands"

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    def start(self) -> None:
        def _on_connect(_client: mqtt.Client, _userdata: Any, _flags: Any, rc: int) -> None:
            if rc == 0:
                self._client.subscribe(self._telemetry_topic)
                self._client.subscribe(self._status_topic)
                self._connected.set()

        self._client.on_connect = _on_connect
        last_err: Exception | None = None
        for _ in range(10):
            try:
                self._client.connect(self.host, self.port, keepalive=30)
                self._client.loop_start()
                return
            except Exception as e:
                last_err = e
                time.sleep(1.5)
        # Если MQTT недоступен, backend всё равно поднимется,
        # но телеметрия устройств не будет приниматься.
        # Ошибку можно будет увидеть в логах.
        if last_err:
            print("MQTT connect failed:", last_err)

    def stop(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass

    def _purge_old_nonces(self, now_ts: int) -> None:
        ttl = self.allowed_drift_seconds * 2
        to_delete = []
        for k, created_ts in self.recent_nonces.items():
            if now_ts - created_ts > ttl:
                to_delete.append(k)
        for k in to_delete:
            self.recent_nonces.pop(k, None)

    def _hmac_signature(self, device_secret: str, base_str: str) -> str:
        raw = hmac.new(device_secret.encode("utf-8"), base_str.encode("utf-8"), sha256).hexdigest()
        return raw

    def _verify_and_mark_nonce(
        self, msg_type: str, device_uid: str, nonce: str, ts: int, device_secret: str
    ) -> bool:
        now_ts = int(time.time())
        if abs(now_ts - ts) > self.allowed_drift_seconds:
            return False

        nonce_key = f"{msg_type}|{device_uid}|{nonce}"
        with self._nonce_lock:
            self._purge_old_nonces(now_ts)
            if nonce_key in self.recent_nonces:
                return False
            self.recent_nonces[nonce_key] = now_ts

        # Проверка подписи — уже после анти-replay, чтобы не тратить вычисления на повторы.
        return True

    def _load_device(self, db: Session, device_uid: str) -> Device | None:
        return db.query(Device).filter(Device.device_uid == device_uid).first()

    def _json_load(self, payload: bytes) -> dict[str, Any] | None:
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception:
            return None

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        topic = msg.topic or ""
        payload = self._json_load(msg.payload or b"")
        if not payload:
            return

        # topics: <base_topic>/<device_uid>/telemetry|status
        parts = topic.split("/")
        if len(parts) < 3:
            return

        device_uid = parts[-2]
        suffix = parts[-1]

        db = SessionLocal()
        try:
            device = self._load_device(db, device_uid)
            if not device:
                return

            # Общие поля
            signature = payload.get("signature")
            ts = payload.get("ts")
            nonce = payload.get("nonce")
            if signature is None or ts is None or nonce is None:
                return

            if suffix == "telemetry":
                sensor_type = payload.get("sensor_type")
                value = payload.get("value")
                if sensor_type is None or value is None:
                    return

                msg_type = "telemetry"
                base_str = (
                    f"{msg_type}|{device_uid}|{sensor_type}|{value}|{ts}|{nonce}"
                )
                expected_sig = self._hmac_signature(device.device_secret, base_str)
                if not hmac.compare_digest(expected_sig, str(signature)):
                    return

                if not self._verify_and_mark_nonce(msg_type, device_uid, str(nonce), int(ts), device.device_secret):
                    return

                create_sensor_data(
                    db=db,
                    device_uid=device_uid,
                    value=float(value),
                    sensor_type=str(sensor_type),
                )
                return

            if suffix == "status":
                actuator_type = payload.get("actuator_type")
                state = payload.get("state")
                if actuator_type is None or state is None:
                    return

                msg_type = "status"
                base_str = f"{msg_type}|{device_uid}|{actuator_type}|{state}|{ts}|{nonce}"
                expected_sig = self._hmac_signature(device.device_secret, base_str)
                if not hmac.compare_digest(expected_sig, str(signature)):
                    return

                if not self._verify_and_mark_nonce(msg_type, device_uid, str(nonce), int(ts), device.device_secret):
                    return

                set_actuator_state(
                    db=db,
                    device_uid=device_uid,
                    action=str(state),
                    actuator_type=str(actuator_type),
                )
                return

        finally:
            db.close()

    def publish_actuator_command(
        self, device_uid: str, actuator_type: str, action: str
    ) -> bool:
        db = SessionLocal()
        try:
            device = self._load_device(db, device_uid)
            if not device:
                return False

            now_ts = int(time.time())
            nonce = str(uuid.uuid4())
            msg_type = "commands"
            base_str = f"{msg_type}|{device_uid}|{action}|{actuator_type}|{now_ts}|{nonce}"
            signature = self._hmac_signature(device.device_secret, base_str)

            payload = {
                "device_uid": device_uid,
                "actuator_type": actuator_type,
                "action": action,
                "ts": now_ts,
                "nonce": nonce,
                "signature": signature,
            }

            topic = self._commands_topic_template.format(device_uid=device_uid)
            self._client.publish(topic, json.dumps(payload), qos=0, retain=False)
            return True
        finally:
            db.close()

    def is_command_subscribed(self) -> bool:
        # backend не подписывается на команды устройств (в текущей лабе команды идут backend -> устройства)
        return False

