import ipaddress
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import docker
from docker.errors import APIError, NotFound
from docker.types import Mount

from manager.cert_lifecycle import DeviceCertLifecycle
from manager import naming


@dataclass
class DockerRuntimeConfig:
    sensor_ip_range: str
    actuator_ip_range: str
    stop_timeout_seconds: int
    auto_restart_max_retries: int
    device_image: str
    mqtt_broker_host: str
    mqtt_broker_port: str
    mqtt_tls_enabled: bool
    mqtt_tls_ca_cert: str
    mqtt_tls_insecure: bool
    mqtt_tls_client_cert: str
    mqtt_tls_client_key: str
    mqtt_username_device: str
    mqtt_password_device: str
    backend_url: str
    device_runtime_secrets_volume: str
    mqtt_shared_certs_volume: str
    mqtt_device_certs_subdir: str
    runtime_secrets_dir: str
    device_group_project: str
    device_group_service: str


class DockerRuntimeManager:
    def __init__(
        self,
        config: DockerRuntimeConfig,
        cert_lifecycle: DeviceCertLifecycle,
        device_command: Callable[[str], str],
        now_iso: Callable[[], str],
    ) -> None:
        self.config = config
        self.cert_lifecycle = cert_lifecycle
        self.device_command = device_command
        self.now_iso = now_iso

    @staticmethod
    def _parse_ip_range(raw_range: str) -> list[str]:
        start_raw, end_raw = [part.strip() for part in raw_range.split("-", 1)]
        start_ip = ipaddress.ip_address(start_raw)
        end_ip = ipaddress.ip_address(end_raw)
        if int(end_ip) < int(start_ip):
            raise ValueError(f"Invalid IP range: {raw_range}")
        return [str(ipaddress.ip_address(value)) for value in range(int(start_ip), int(end_ip) + 1)]

    def _device_labels(self, device_uid: str, device_type: str) -> dict[str, str]:
        return {
            "project": "greenhouse",
            "managed_by": "sensor_manager",
            "domain": "device",
            "group": "devices",
            "device_role": "sensor" if naming.is_sensor(device_type) else "actuator",
            "device_uid": device_uid,
            "device_type": device_type,
            "com.docker.compose.project": self.config.device_group_project,
            "com.docker.compose.service": self.config.device_group_service,
        }

    def _allocate_ip(self, device_uid: str, device_type: str, devices_state: dict) -> str:
        wanted_pool = self._parse_ip_range(
            self.config.sensor_ip_range if naming.is_sensor(device_type) else self.config.actuator_ip_range
        )
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

    @staticmethod
    def _get_container(client: docker.DockerClient, container_name: str):
        try:
            return client.containers.get(container_name)
        except NotFound:
            return None

    def _ensure_device_mtls_material(self, device_uid: str, info: dict) -> tuple[str | None, str | None]:
        if not self.config.mqtt_tls_enabled:
            return None, None
        cert_path, key_path = self.cert_lifecycle.device_paths(device_uid)
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        if (
            cert_path.is_file()
            and key_path.is_file()
            and cert_path.stat().st_size > 0
            and key_path.stat().st_size > 0
        ):
            info["mtls_cert_path"] = str(cert_path)
            info["mtls_key_path"] = str(key_path)
            return str(cert_path), str(key_path)
        try:
            cert_path.unlink(missing_ok=True)
        except OSError:
            pass

        cert_path_s, key_path_s = self.cert_lifecycle.issue(device_uid)
        info["mtls_cert_path"] = str(cert_path)
        info["mtls_key_path"] = str(key_path)
        print(f"[manager] generated per-device mTLS cert for {device_uid}")
        return cert_path_s, key_path_s

    def ensure_created(
        self,
        client: docker.DockerClient,
        network,
        state: dict,
        device_uid: str,
        device_type: str,
        device_token: str | None,
    ):
        devices_state = state["devices"]
        info = devices_state.setdefault(device_uid, {})
        assigned_ip = self._allocate_ip(device_uid, device_type, devices_state)
        desired_name = naming.container_name(device_uid, device_type)
        stored_name = str(info.get("container_name") or "").strip()
        if stored_name.startswith("greenhouse_device_"):
            info["container_name"] = desired_name
            stored_name = desired_name
        container_name = stored_name or desired_name
        container = self._get_container(client, container_name)

        if container is None:
            legacy_name = naming.legacy_container_name(device_uid)
            legacy_container = self._get_container(client, legacy_name)
            if legacy_container is not None:
                legacy_container.rename(desired_name)
                container_name = desired_name
                info["container_name"] = desired_name
                container = self._get_container(client, desired_name)
                print(
                    f"[manager] renamed container {legacy_name} -> {desired_name} "
                    f"for {device_uid}"
                )

        if container is None:
            command = self.device_command(device_type)
            effective_token = device_token
            if effective_token is None:
                remembered = str(info.get("synced_device_token") or "").strip()
                effective_token = remembered if remembered else None
            client_cert_path, client_key_path = self._ensure_device_mtls_material(device_uid, info)
            cert_mount_dir = f"/mqtt-certs/{self.config.mqtt_device_certs_subdir}"
            cert_mount_base = cert_mount_dir.rstrip("/")
            cert_basename = naming.device_secret_basename(device_uid)
            env = {
                "DEVICE_UID": device_uid,
                "DEVICE_TOKEN": effective_token,
                "BACKEND_URL": self.config.backend_url,
                "MQTT_BROKER_HOST": self.config.mqtt_broker_host,
                "MQTT_BROKER_PORT": str(self.config.mqtt_broker_port),
                "MQTT_TLS_ENABLED": "true" if self.config.mqtt_tls_enabled else "false",
                "MQTT_TLS_CA_CERT": self.config.mqtt_tls_ca_cert,
                "MQTT_TLS_INSECURE": "true" if self.config.mqtt_tls_insecure else "false",
                "MQTT_TLS_CLIENT_CERT": (
                    f"{cert_mount_base}/{cert_basename}.crt"
                    if client_cert_path
                    else self.config.mqtt_tls_client_cert
                ),
                "MQTT_TLS_CLIENT_KEY": (
                    f"{cert_mount_base}/{cert_basename}.key"
                    if client_key_path
                    else self.config.mqtt_tls_client_key
                ),
                "MQTT_USERNAME": self.config.mqtt_username_device,
                "MQTT_PASSWORD": self.config.mqtt_password_device,
                "ACTUATOR_TYPE": device_type,
                "RUNTIME_SECRETS_DIR": "/runtime-secrets",
            }
            env = {k: v for k, v in env.items() if v is not None}
            mounts = []
            if self.config.device_runtime_secrets_volume:
                mounts.append(
                    Mount(
                        target="/runtime-secrets",
                        source=self.config.device_runtime_secrets_volume,
                        type="volume",
                        read_only=True,
                    )
                )
            if self.config.mqtt_shared_certs_volume:
                mounts.append(
                    Mount(
                        target="/mqtt-certs",
                        source=self.config.mqtt_shared_certs_volume,
                        type="volume",
                        read_only=True,
                    )
                )
            create_kw: dict = {
                "image": self.config.device_image,
                "name": container_name,
                "command": ["sh", "-c", command],
                "detach": True,
                "environment": env,
                "labels": self._device_labels(device_uid=device_uid, device_type=device_type),
            }
            if mounts:
                create_kw["mounts"] = mounts
            container = client.containers.create(**create_kw)
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
                "updated_at": self.now_iso(),
            }
        )
        return container, info

    def ensure_stopped(self, container, info: dict) -> None:
        container.reload()
        if container.status == "running":
            container.stop(timeout=self.config.stop_timeout_seconds)
            container.reload()
        info["actual_runtime_state"] = "stopped"
        info["status"] = "provisioned"
        info["updated_at"] = self.now_iso()

    def ensure_running(self, container, info: dict) -> None:
        container.reload()
        if container.status != "running":
            container.start()
            container.reload()
        info["actual_runtime_state"] = "running"
        info["status"] = "running"
        info["updated_at"] = self.now_iso()

    def ensure_removed(self, client: docker.DockerClient, state: dict, device_uid: str) -> None:
        info = state["devices"].get(device_uid)
        if not info:
            return
        container_name = info.get("container_name") or naming.container_name(
            device_uid, str(info.get("device_type", ""))
        )
        container = self._get_container(client, container_name)
        if container is None:
            container = self._get_container(client, naming.legacy_container_name(device_uid))
        if container is not None:
            try:
                container.stop(timeout=self.config.stop_timeout_seconds)
            except APIError:
                pass
            container.remove(force=True)
            print(f"[manager] removed container {container_name} ({device_uid})")
        state["devices"].pop(device_uid, None)
        if self.config.runtime_secrets_dir:
            try:
                secret = Path(self.config.runtime_secrets_dir) / f"{naming.device_secret_basename(device_uid)}.json"
                if secret.is_file():
                    secret.unlink()
            except OSError:
                pass

    def health_check(self, client: docker.DockerClient, state: dict) -> None:
        for device_uid, info in list(state.get("devices", {}).items()):
            container_name = info.get("container_name") or naming.container_name(
                device_uid, str(info.get("device_type", ""))
            )
            container = self._get_container(client, container_name)
            if container is None:
                container = self._get_container(client, naming.legacy_container_name(device_uid))
            if container is None:
                info["actual_runtime_state"] = "missing"
                info["last_error"] = "container not found"
                continue

            container.reload()
            info["actual_runtime_state"] = container.status
            info["updated_at"] = self.now_iso()
            wants_running = info.get("desired_runtime_state") == "running"
            if wants_running and container.status != "running":
                retries = int(info.get("restart_count", 0))
                if retries < self.config.auto_restart_max_retries:
                    try:
                        container.restart(timeout=self.config.stop_timeout_seconds)
                        info["restart_count"] = retries + 1
                        info["last_error"] = None
                        print(f"[manager] auto-restart {device_uid} attempt={retries + 1}")
                    except APIError as exc:
                        info["last_error"] = f"restart failed: {exc}"
                else:
                    info["last_error"] = "auto-restart limit reached"

    def stop_all_managed(self, client: docker.DockerClient, state: dict) -> None:
        for info in list(state.get("devices", {}).values()):
            container_name = info.get("container_name")
            if not container_name:
                continue
            container = self._get_container(client, container_name)
            if container is None:
                continue
            try:
                container.stop(timeout=self.config.stop_timeout_seconds)
                info["actual_runtime_state"] = "stopped"
            except APIError as exc:
                info["last_error"] = f"stop failed on shutdown: {exc}"
            info["updated_at"] = self.now_iso()
