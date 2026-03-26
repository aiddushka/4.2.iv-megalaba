import argparse
import os
import sys
import time
import uuid
from threading import Lock

import paho.mqtt.client as mqtt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mqtt_common import command_base_str, mqtt_topic, sign_hmac_hex, status_base_str, to_json  # noqa: E402
from http_client import http_get_json


ACTUATOR_TYPE = "HEATER_ACTUATOR"


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT heater actuator emulator")
    parser.add_argument("--device_uid", required=True)
    parser.add_argument("--device_secret", required=True)
    parser.add_argument("--mqtt_host", required=True)
    parser.add_argument("--mqtt_port", type=int, default=1883)
    parser.add_argument("--period_seconds", type=float, default=5)
    args = parser.parse_args()

    device_uid = args.device_uid
    device_secret = args.device_secret
    mqtt_host = args.mqtt_host
    mqtt_port = args.mqtt_port
    status_period = float(args.period_seconds)

    base_topic = os.getenv("MQTT_BASE_TOPIC", "greenhouse/devices")
    commands_topic = mqtt_topic(base_topic, device_uid, "commands")
    status_topic = mqtt_topic(base_topic, device_uid, "status")

    client = mqtt.Client()
    state_lock = Lock()
    state = "OFF"
    auto_off_at: float | None = None

    used_nonces: set[str] = set()
    allowed_drift = int(os.getenv("MQTT_ALLOWED_DRIFT_SECONDS", "300"))

    default_on_duration_seconds = 25.0
    on_duration_seconds: float = default_on_duration_seconds
    config_poll_seconds = float(os.getenv("CONFIG_POLL_SECONDS", "10"))
    last_poll = 0.0

    def publish_status() -> None:
        nonlocal state
        ts = int(time.time())
        nonce = str(uuid.uuid4())
        with state_lock:
            current_state = state
        base_str = status_base_str(device_uid, ACTUATOR_TYPE, current_state, ts, nonce)
        signature = sign_hmac_hex(device_secret, base_str)
        payload = {
            "device_uid": device_uid,
            "actuator_type": ACTUATOR_TYPE,
            "state": current_state,
            "ts": ts,
            "nonce": nonce,
            "signature": signature,
        }
        client.publish(status_topic, to_json(payload), qos=0, retain=False)

    def on_message(_client: mqtt.Client, _userdata: object, msg: mqtt.MQTTMessage) -> None:
        nonlocal state, auto_off_at
        try:
            data = __import__("json").loads(msg.payload.decode("utf-8"))
        except Exception:
            return

        action = data.get("action")
        actuator_type = data.get("actuator_type")
        ts = data.get("ts")
        nonce = data.get("nonce")
        signature = data.get("signature")
        if (
            action is None
            or actuator_type is None
            or ts is None
            or nonce is None
            or signature is None
        ):
            return
        if str(actuator_type) != ACTUATOR_TYPE:
            return

        ts = int(ts)
        now_ts = int(time.time())
        if abs(now_ts - ts) > allowed_drift:
            return
        nonce = str(nonce)
        if nonce in used_nonces:
            return
        used_nonces.add(nonce)

        base_str = command_base_str(device_uid, ACTUATOR_TYPE, str(action), ts, nonce)
        expected_sig = sign_hmac_hex(device_secret, base_str)
        if str(signature) != expected_sig:
            return

        action = str(action).upper()
        if action not in {"ON", "OFF"}:
            return

        with state_lock:
            state = action
            if action == "ON":
                auto_off_at = time.time() + on_duration_seconds
            else:
                auto_off_at = None

        publish_status()

    client.on_message = on_message
    client.connect(mqtt_host, mqtt_port, keepalive=30)
    client.subscribe(commands_topic, qos=0)
    client.loop_start()

    publish_status()
    last_status_ts = 0.0

    while True:
        now = time.time()
        if now - last_poll >= config_poll_seconds:
            last_poll = now
            try:
                cfg_url = f"{os.getenv('HTTP_BASE_URL', 'http://localhost:8000')}/devices/{device_uid}/config"
                cfg = http_get_json(cfg_url, timeout_seconds=5.0)
                cc = cfg.get("config_settings", {}) or {}
                if cc.get("on_duration_seconds") is not None:
                    on_duration_seconds = float(cc["on_duration_seconds"])
            except Exception:
                pass
        time.sleep(0.5)
        now = time.time()
        if auto_off_at is not None and now >= auto_off_at:
            with state_lock:
                if state == "ON":
                    state = "OFF"
            auto_off_at = None
            publish_status()

        if now - last_status_ts >= status_period:
            last_status_ts = now
            publish_status()


if __name__ == "__main__":
    main()

