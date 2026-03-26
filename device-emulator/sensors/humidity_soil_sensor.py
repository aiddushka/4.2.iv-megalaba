import argparse
import os
import random
import sys
import time
import uuid

import paho.mqtt.client as mqtt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mqtt_common import mqtt_topic, sign_hmac_hex, status_base_str, telemetry_base_str, to_json  # noqa: E402,F401
from http_client import http_get_json


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT soil humidity sensor emulator")
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
    period_seconds = float(args.period_seconds)

    sensor_type = "HUMIDITY_SOIL_SENSOR"
    base_topic = os.getenv("MQTT_BASE_TOPIC", "greenhouse/devices")
    telemetry_topic = mqtt_topic(base_topic, device_uid, "telemetry")

    # Внутреннее состояние: влажность почвы меняется медленно.
    soil_moisture = random.uniform(35.0, 55.0)

    client = mqtt.Client()
    client.connect(mqtt_host, mqtt_port, keepalive=30)
    client.loop_start()

    min_value: float | None = None
    max_value: float | None = None
    calibration_offset: float = 0.0
    frequency_seconds: float = period_seconds
    config_poll_seconds = float(os.getenv("CONFIG_POLL_SECONDS", "10"))
    last_poll = 0.0

    while True:
        now = time.time()
        if now - last_poll >= config_poll_seconds:
            last_poll = now
            try:
                cfg_url = f"{os.getenv('HTTP_BASE_URL', 'http://localhost:8000')}/sensors/{device_uid}/threshold"
                cfg = http_get_json(cfg_url, timeout_seconds=5.0)
                params = cfg.get("parameters", {}) or {}
                if params.get("min_value") is not None:
                    min_value = float(params["min_value"])
                if params.get("max_value") is not None:
                    max_value = float(params["max_value"])
                if params.get("calibration_offset") is not None:
                    calibration_offset = float(params["calibration_offset"])
                if params.get("frequency_seconds") is not None:
                    frequency_seconds = float(params["frequency_seconds"])
            except Exception:
                pass

        # Испарение/высыхание (медленно уменьшаем влажность)
        evap = random.uniform(0.03, 0.10)
        soil_moisture -= evap

        # Редкие "поливы" для правдоподобия, если реальных команд нет.
        if random.random() < 0.03:
            soil_moisture += random.uniform(8.0, 18.0)

        # Небольшой шум датчика
        soil_moisture += random.gauss(0, 0.25)
        soil_moisture = max(0.0, min(100.0, soil_moisture))
        value = float(round(soil_moisture, 2)) + calibration_offset
        if min_value is not None:
            value = max(min_value, value)
        if max_value is not None:
            value = min(max_value, value)

        ts = int(time.time())
        nonce = str(uuid.uuid4())
        base_str = telemetry_base_str(device_uid, sensor_type, value, ts, nonce)
        signature = sign_hmac_hex(device_secret, base_str)

        payload = {
            "device_uid": device_uid,
            "sensor_type": sensor_type,
            "value": value,
            "ts": ts,
            "nonce": nonce,
            "signature": signature,
        }
        client.publish(telemetry_topic, to_json(payload), qos=0, retain=False)
        sleep_seconds = frequency_seconds if frequency_seconds > 0 else period_seconds
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()

