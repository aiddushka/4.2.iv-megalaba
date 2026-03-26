import argparse
import math
import os
import random
import sys
import time
import uuid

import paho.mqtt.client as mqtt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mqtt_common import mqtt_topic, sign_hmac_hex, telemetry_base_str, to_json  # noqa: E402


def _now_cycle_fraction() -> float:
    t = time.localtime()
    seconds = t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec
    return seconds / 86400.0


def generate_air_humidity_percent() -> float:
    # Воздух: более влажно ночью, более сухо днём
    frac = _now_cycle_fraction()
    daily = math.sin(2 * math.pi * frac)
    base = 62.0
    amplitude = 10.0
    noise = random.gauss(0, 0.6)
    # Корреляция с температурным профилем (фактически просто "правдоподобный" синус)
    humidity = base - amplitude * daily + noise
    humidity = max(0.0, min(100.0, humidity))
    return round(humidity, 2)


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT air humidity sensor emulator")
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

    sensor_type = "humidity_air"
    base_topic = os.getenv("MQTT_BASE_TOPIC", "greenhouse/devices")
    telemetry_topic = mqtt_topic(base_topic, device_uid, "telemetry")

    client = mqtt.Client()
    client.connect(mqtt_host, mqtt_port, keepalive=30)
    client.loop_start()

    while True:
        value = generate_air_humidity_percent()
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
        time.sleep(period_seconds)


if __name__ == "__main__":
    main()

