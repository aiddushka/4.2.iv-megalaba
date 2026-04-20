import signal
import sys
import time

import docker
from manager.cert_lifecycle import DeviceCertLifecycle
from manager.config import ManagerConfig
from manager.docker_runtime import DockerRuntimeManager
from manager.orchestration_api import OrchestrationApiClient
from manager.reconciler import DeviceReconciler
from manager.state_store import load_state, save_state

CONFIG = ManagerConfig.from_env()

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

CERT_LIFECYCLE = DeviceCertLifecycle(
    certs_rw_dir=CONFIG.mqtt_certs_rw_dir,
    device_ca_cert_path=CONFIG.mqtt_device_ca_cert_path,
    device_ca_key_path=CONFIG.mqtt_device_ca_key_path,
    device_certs_subdir=CONFIG.mqtt_device_certs_subdir,
    device_crl_path=CONFIG.mqtt_device_crl_path,
    broker_container_name=CONFIG.mqtt_broker_container_name,
)
ORCHESTRATION_API = OrchestrationApiClient(
    backend_url=CONFIG.backend_url,
    manager_key=CONFIG.manager_key,
    timeout_seconds=5,
)


def _device_command(device_type: str) -> str:
    script = SENSOR_SCRIPT_BY_DEVICE_TYPE.get(device_type)
    if script:
        return f"python -u {script}"
    actuator_script = ACTUATOR_SCRIPT_BY_DEVICE_TYPE.get(device_type)
    if actuator_script:
        return f"python -u {actuator_script}"
    return "python -u -c \"import time; print('unsupported device type'); time.sleep(10**9)\""


RUNTIME_MANAGER = DockerRuntimeManager(
    config=CONFIG.to_runtime_config(),
    cert_lifecycle=CERT_LIFECYCLE,
    device_command=_device_command,
    now_iso=_now_iso,
)
RECONCILER = DeviceReconciler(
    runtime_manager=RUNTIME_MANAGER,
    orchestration_api=ORCHESTRATION_API,
    runtime_secrets_dir=CONFIG.runtime_secrets_dir,
)


running = True


def _shutdown_handler(_signum, _frame):
    global running
    running = False


signal.signal(signal.SIGTERM, _shutdown_handler)
signal.signal(signal.SIGINT, _shutdown_handler)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] in {"issue", "rotate", "revoke"}:
        action = sys.argv[1]
        uid = sys.argv[2]
        CERT_LIFECYCLE.run_cli_action(action, uid)
        raise SystemExit(0)

    client = docker.from_env()
    network = client.networks.get(CONFIG.device_network_name)
    state = load_state(CONFIG.state_file_path, CONFIG.state_schema_version, _now_iso)
    last_healthcheck_at = 0.0

    print(f"[manager] polling orchestration state: {CONFIG.orchestration_state_url}")
    while running:
        desired_devices = ORCHESTRATION_API.fetch_orchestration_state()
        if desired_devices is not None:
            desired_uids = {item.get("device_uid") for item in desired_devices if item.get("device_uid")}

            for desired_device in desired_devices:
                try:
                    RECONCILER.reconcile_device(client, network, state, desired_device)
                except Exception as exc:
                    uid = desired_device.get("device_uid", "unknown")
                    print(f"[manager] reconcile failed for {uid}: {exc}")
                    info = state["devices"].setdefault(uid, {})
                    info["last_error"] = str(exc)
                    info["updated_at"] = _now_iso()

            # Удаляем контейнеры только если устройство реально отсутствует в backend.
            stale_uids = [uid for uid in list(state["devices"].keys()) if uid not in desired_uids]
            for stale_uid in stale_uids:
                RUNTIME_MANAGER.ensure_removed(client, state, stale_uid)

        now = time.time()
        if now - last_healthcheck_at >= CONFIG.healthcheck_interval_seconds:
            RUNTIME_MANAGER.health_check(client, state)
            last_healthcheck_at = now

        save_state(CONFIG.state_file_path, state, CONFIG.state_schema_version, _now_iso)
        time.sleep(CONFIG.poll_interval_seconds)

    print("[manager] shutdown signal received, stopping managed containers...")
    RUNTIME_MANAGER.stop_all_managed(client, state)
    save_state(CONFIG.state_file_path, state, CONFIG.state_schema_version, _now_iso)
    print("[manager] shutdown complete")
