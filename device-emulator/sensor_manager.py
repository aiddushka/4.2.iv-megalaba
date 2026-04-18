import ipaddress
import json
import os
import signal
import time
from pathlib import Path

import docker
import requests
from docker.errors import APIError, NotFound


BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
ORCHESTRATION_STATE_URL = f"{BACKEND_URL}/devices/internal/orchestration-state"
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))
HEALTHCHECK_INTERVAL_SECONDS = int(os.getenv("HEALTHCHECK_INTERVAL_SECONDS", "10"))
STATE_FILE_PATH = Path(os.getenv("STATE_FILE_PATH", "/app/state.json"))
STATE_SCHEMA_VERSION = 1
DEVICE_NETWORK_NAME = os.getenv("DEVICE_NETWORK_NAME", "greenhouse_iot_net")
DEVICE_IMAGE = os.getenv("DEVICE_IMAGE", "docker-device-runtime")
SENSOR_IP_RANGE = os.getenv("SENSOR_IP_RANGE", "172.28.1.10-172.28.1.250")
ACTUATOR_IP_RANGE = os.getenv("ACTUATOR_IP_RANGE", "172.28.2.10-172.28.2.250")
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = os.getenv("MQTT_BROKER_PORT", "1883")
AUTO_RESTART_MAX_RETRIES = int(os.getenv("AUTO_RESTART_MAX_RETRIES", "5"))
STOP_TIMEOUT_SECONDS = int(os.getenv("STOP_TIMEOUT_SECONDS", "10"))
DEVICE_GROUP_PROJECT = os.getenv("DEVICE_GROUP_PROJECT", "devices")
DEVICE_GROUP_SERVICE = os.getenv("DEVICE_GROUP_SERVICE", "device-runtime")
MANAGER_KEY = os.getenv("MANAGER_KEY", "")

SENSOR_SCRIPT_BY_DEVICE_TYPE = {
    "TEMP_SENSOR": "sensors/temperature_sensor.py",
    "HUMIDITY_AIR_SENSOR": "sensors/humidity_air_sensor.py",
    "HUMIDITY_SOIL_SENSOR": "sensors/humidity_soil_sensor.py",
    "LIGHT_SENSOR": "sensors/light_sensor.py",
}
ACTUATOR_SCRIPT_BY_DEVICE_TYPE = {
    "HEATER_ACTUATOR": "actuators/heater.py",
    "VENTILATION_ACTUATOR": "actuators/ventilation.py",
    "IRRIGATION_ACTUATOR": "actuators/irrigation.py",
    "LIGHT_ACTUATOR": "actuators/light.py",
}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _parse_ip_range(raw_range: str) -> list[str]:
    start_raw, end_raw = [part.strip() for part in raw_range.split("-", 1)]
    start_ip = ipaddress.ip_address(start_raw)
    end_ip = ipaddress.ip_address(end_raw)
    if int(end_ip) < int(start_ip):
        raise ValueError(f"Invalid IP range: {raw_range}")
    return [str(ipaddress.ip_address(value)) for value in range(int(start_ip), int(end_ip) + 1)]


def _is_sensor(device_type: str) -> bool:
    return "SENSOR" in (device_type or "")


def _container_name(device_uid: str) -> str:
    safe_uid = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in device_uid)
    return f"greenhouse_device_{safe_uid}".lower()


def _device_labels(device_uid: str, device_type: str) -> dict[str, str]:
    return {
        "project": "greenhouse",
        "managed_by": "sensor_manager",
        "domain": "device",
        "group": "devices",
        "device_uid": device_uid,
        "device_type": device_type,
        # Compose-style labels improve grouping in Docker Desktop UI.
        "com.docker.compose.project": DEVICE_GROUP_PROJECT,
        "com.docker.compose.service": DEVICE_GROUP_SERVICE,
    }


def _load_state() -> dict:
    if not STATE_FILE_PATH.exists():
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "updated_at": _now_iso(),
            "devices": {},
        }
    try:
        payload = json.loads(STATE_FILE_PATH.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("State file is not an object")
        payload.setdefault("schema_version", STATE_SCHEMA_VERSION)
        payload.setdefault("updated_at", _now_iso())
        payload.setdefault("devices", {})
        if not isinstance(payload["devices"], dict):
            payload["devices"] = {}
        return payload
    except Exception as exc:
        print(f"[manager] state load failed, fallback to empty state: {exc}")
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "updated_at": _now_iso(),
            "devices": {},
        }


def _save_state(state: dict) -> None:
    state["schema_version"] = STATE_SCHEMA_VERSION
    state["updated_at"] = _now_iso()
    STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = STATE_FILE_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")
    temp_path.replace(STATE_FILE_PATH)


def _fetch_orchestration_state() -> list[dict] | None:
    try:
        headers = {"X-Manager-Key": MANAGER_KEY} if MANAGER_KEY else {}
        response = requests.get(ORCHESTRATION_STATE_URL, timeout=5, headers=headers)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
    except Exception as exc:
        print(f"[manager] failed to fetch orchestration state: {exc}")
    return None


def _device_command(device_type: str) -> str:
    script = SENSOR_SCRIPT_BY_DEVICE_TYPE.get(device_type)
    if script:
        return f"python -u {script}"
    actuator_script = ACTUATOR_SCRIPT_BY_DEVICE_TYPE.get(device_type)
    if actuator_script:
        return f"python -u {actuator_script}"
    return "python -u -c \"import time; print('unsupported device type'); time.sleep(10**9)\""


def _allocate_ip(device_uid: str, device_type: str, devices_state: dict) -> str:
    wanted_pool = _parse_ip_range(SENSOR_IP_RANGE if _is_sensor(device_type) else ACTUATOR_IP_RANGE)
    used_ips = {
        entry.get("assigned_ip")
        for uid, entry in devices_state.items()
        if uid != device_uid and entry.get("assigned_ip")
    }
    current = devices_state.get(device_uid, {}).get("assigned_ip")
    if current and current in wanted_pool and current not in used_ips:
        return current
    for ip_value in wanted_pool:
        if ip_value not in used_ips:
            return ip_value
    raise RuntimeError(f"No free IP for {device_uid} ({device_type})")


def _get_container(client: docker.DockerClient, container_name: str):
    try:
        return client.containers.get(container_name)
    except NotFound:
        return None


def _ensure_created(
    client: docker.DockerClient,
    network,
    state: dict,
    device_uid: str,
    device_type: str,
    device_token: str | None,
):
    devices_state = state["devices"]
    info = devices_state.setdefault(device_uid, {})
    assigned_ip = _allocate_ip(device_uid, device_type, devices_state)
    container_name = info.get("container_name") or _container_name(device_uid)
    container = _get_container(client, container_name)

    if container is None:
        command = _device_command(device_type)
        env = {
            "DEVICE_UID": device_uid,
            "DEVICE_TOKEN": device_token,
            "BACKEND_URL": BACKEND_URL,
            "MQTT_BROKER_HOST": MQTT_BROKER_HOST,
            "MQTT_BROKER_PORT": str(MQTT_BROKER_PORT),
            "ACTUATOR_TYPE": device_type,
        }
        env = {k: v for k, v in env.items() if v is not None}
        container = client.containers.create(
            image=DEVICE_IMAGE,
            name=container_name,
            command=["sh", "-c", command],
            detach=True,
            environment=env,
            labels=_device_labels(device_uid=device_uid, device_type=device_type),
        )
        network.connect(container, ipv4_address=assigned_ip)
        print(f"[manager] created container {container_name} for {device_uid} ip={assigned_ip}")

    info.update(
        {
            "device_uid": device_uid,
            "device_type": device_type,
            "container_id": container.id,
            "container_name": container_name,
            "assigned_ip": assigned_ip,
            "status": info.get("status", "created"),
            "desired_runtime_state": info.get("desired_runtime_state", "stopped"),
            "actual_runtime_state": info.get("actual_runtime_state", "created"),
            "restart_count": int(info.get("restart_count", 0)),
            "last_error": None,
            "updated_at": _now_iso(),
        }
    )
    return container, info


def _ensure_stopped(container, info: dict) -> None:
    container.reload()
    if container.status == "running":
        container.stop(timeout=STOP_TIMEOUT_SECONDS)
        container.reload()
    info["actual_runtime_state"] = "stopped"
    info["status"] = "provisioned"
    info["updated_at"] = _now_iso()


def _ensure_running(container, info: dict) -> None:
    container.reload()
    if container.status != "running":
        container.start()
        container.reload()
    info["actual_runtime_state"] = "running"
    info["status"] = "running"
    info["updated_at"] = _now_iso()


def _ensure_removed(client: docker.DockerClient, state: dict, device_uid: str) -> None:
    info = state["devices"].get(device_uid)
    if not info:
        return
    container_name = info.get("container_name") or _container_name(device_uid)
    container = _get_container(client, container_name)
    if container is not None:
        try:
            container.stop(timeout=STOP_TIMEOUT_SECONDS)
        except APIError:
            pass
        container.remove(force=True)
        print(f"[manager] removed container {container_name} ({device_uid})")
    state["devices"].pop(device_uid, None)


def _reconcile_device(client: docker.DockerClient, network, state: dict, desired: dict) -> None:
    device_uid = desired.get("device_uid")
    device_type = desired.get("device_type")
    desired_runtime_state = desired.get("desired_runtime_state", "stopped")
    device_token = desired.get("device_token")
    if not device_uid or not device_type:
        return

    if desired_runtime_state == "removed":
        _ensure_removed(client, state, device_uid)
        return

    container, info = _ensure_created(client, network, state, device_uid, device_type, device_token)
    info["desired_runtime_state"] = desired_runtime_state
    info["status"] = desired.get("status", info.get("status"))

    if desired_runtime_state == "running":
        _ensure_running(container, info)
    else:
        _ensure_stopped(container, info)


def _health_check(client: docker.DockerClient, state: dict) -> None:
    for device_uid, info in list(state.get("devices", {}).items()):
        container_name = info.get("container_name") or _container_name(device_uid)
        container = _get_container(client, container_name)
        if container is None:
            info["actual_runtime_state"] = "missing"
            info["last_error"] = "container not found"
            continue

        container.reload()
        info["actual_runtime_state"] = container.status
        info["updated_at"] = _now_iso()
        wants_running = info.get("desired_runtime_state") == "running"
        if wants_running and container.status != "running":
            retries = int(info.get("restart_count", 0))
            if retries < AUTO_RESTART_MAX_RETRIES:
                try:
                    container.restart(timeout=STOP_TIMEOUT_SECONDS)
                    info["restart_count"] = retries + 1
                    info["last_error"] = None
                    print(f"[manager] auto-restart {device_uid} attempt={retries + 1}")
                except APIError as exc:
                    info["last_error"] = f"restart failed: {exc}"
            else:
                info["last_error"] = "auto-restart limit reached"


def _stop_all_managed(client: docker.DockerClient, state: dict) -> None:
    for info in list(state.get("devices", {}).values()):
        container_name = info.get("container_name")
        if not container_name:
            continue
        container = _get_container(client, container_name)
        if container is None:
            continue
        try:
            container.stop(timeout=STOP_TIMEOUT_SECONDS)
            info["actual_runtime_state"] = "stopped"
        except APIError as exc:
            info["last_error"] = f"stop failed on shutdown: {exc}"
        info["updated_at"] = _now_iso()


running = True


def _shutdown_handler(_signum, _frame):
    global running
    running = False


signal.signal(signal.SIGTERM, _shutdown_handler)
signal.signal(signal.SIGINT, _shutdown_handler)


if __name__ == "__main__":
    client = docker.from_env()
    network = client.networks.get(DEVICE_NETWORK_NAME)
    state = _load_state()
    last_healthcheck_at = 0.0

    print(f"[manager] polling orchestration state: {ORCHESTRATION_STATE_URL}")
    while running:
        desired_devices = _fetch_orchestration_state()
        if desired_devices is not None:
            desired_uids = {item.get("device_uid") for item in desired_devices if item.get("device_uid")}

            for desired_device in desired_devices:
                try:
                    _reconcile_device(client, network, state, desired_device)
                except Exception as exc:
                    uid = desired_device.get("device_uid", "unknown")
                    print(f"[manager] reconcile failed for {uid}: {exc}")
                    info = state["devices"].setdefault(uid, {})
                    info["last_error"] = str(exc)
                    info["updated_at"] = _now_iso()

            # Удаляем контейнеры только если устройство реально отсутствует в backend.
            stale_uids = [uid for uid in list(state["devices"].keys()) if uid not in desired_uids]
            for stale_uid in stale_uids:
                _ensure_removed(client, state, stale_uid)

        now = time.time()
        if now - last_healthcheck_at >= HEALTHCHECK_INTERVAL_SECONDS:
            _health_check(client, state)
            last_healthcheck_at = now

        _save_state(state)
        time.sleep(POLL_INTERVAL_SECONDS)

    print("[manager] shutdown signal received, stopping managed containers...")
    _stop_all_managed(client, state)
    _save_state(state)
    print("[manager] shutdown complete")
