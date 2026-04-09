import json
import os
import signal
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
ACTIVE_SENSORS_URL = f"{BACKEND_URL}/devices/active-sensors"
POLL_INTERVAL_SECONDS = 5

SCRIPT_BY_DEVICE_TYPE = {
    "TEMP_SENSOR": "sensors/temperature_sensor.py",
    "HUMIDITY_AIR_SENSOR": "sensors/humidity_air_sensor.py",
    "HUMIDITY_SOIL_SENSOR": "sensors/humidity_soil_sensor.py",
    "LIGHT_SENSOR": "sensors/light_sensor.py",
}

processes: dict[str, subprocess.Popen] = {}
running = True


def fetch_active_sensors() -> list[dict]:
    try:
        with urlopen(ACTIVE_SENSORS_URL, timeout=5) as response:
            payload = response.read().decode("utf-8")
            data = json.loads(payload)
            return data if isinstance(data, list) else []
    except (URLError, TimeoutError, json.JSONDecodeError):
        return []


def start_emulator(device_uid: str, device_type: str) -> None:
    script = SCRIPT_BY_DEVICE_TYPE.get(device_type)
    if not script:
        return
    proc = processes.get(device_uid)
    if proc and proc.poll() is None:
        return
    env = dict(os.environ)
    env["DEVICE_UID"] = device_uid
    env["BACKEND_URL"] = BACKEND_URL
    processes[device_uid] = subprocess.Popen([sys.executable, script], env=env)
    print(f"[sensor-manager] started {device_uid} ({device_type})")


def stop_emulator(device_uid: str) -> None:
    proc = processes.get(device_uid)
    if not proc:
        return
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    processes.pop(device_uid, None)
    print(f"[sensor-manager] stopped {device_uid}")


def stop_all() -> None:
    for uid in list(processes.keys()):
        stop_emulator(uid)


def _shutdown_handler(_signum, _frame):
    global running
    running = False


signal.signal(signal.SIGTERM, _shutdown_handler)
signal.signal(signal.SIGINT, _shutdown_handler)


if __name__ == "__main__":
    print(f"[sensor-manager] polling {ACTIVE_SENSORS_URL}")
    while running:
        active_sensors = fetch_active_sensors()
        active_uids = set()
        for sensor in active_sensors:
            device_uid = sensor.get("device_uid")
            device_type = sensor.get("device_type")
            if not device_uid or not device_type:
                continue
            active_uids.add(device_uid)
            start_emulator(device_uid, device_type)
        for uid in list(processes.keys()):
            if uid not in active_uids:
                stop_emulator(uid)
        time.sleep(POLL_INTERVAL_SECONDS)
    stop_all()
