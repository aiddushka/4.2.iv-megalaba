import os
from dataclasses import dataclass
from pathlib import Path

from manager.docker_runtime import DockerRuntimeConfig


@dataclass(frozen=True)
class ManagerConfig:
    backend_url: str
    poll_interval_seconds: int
    healthcheck_interval_seconds: int
    state_file_path: Path
    state_schema_version: int
    device_network_name: str
    manager_key: str

    sensor_ip_range: str
    actuator_ip_range: str
    auto_restart_max_retries: int
    stop_timeout_seconds: int
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
    mqtt_shared_certs_volume: str
    mqtt_certs_rw_dir: str
    mqtt_device_ca_cert_path: str
    mqtt_device_ca_key_path: str
    mqtt_device_certs_subdir: str
    mqtt_device_crl_path: str
    mqtt_broker_container_name: str

    runtime_secrets_dir: str
    device_runtime_secrets_volume: str

    device_group_project: str
    device_group_service: str

    @classmethod
    def from_env(cls) -> "ManagerConfig":
        return cls(
            backend_url=os.getenv("BACKEND_URL", "http://backend:8000"),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "5")),
            healthcheck_interval_seconds=int(os.getenv("HEALTHCHECK_INTERVAL_SECONDS", "10")),
            state_file_path=Path(os.getenv("STATE_FILE_PATH", "/app/state.json")),
            state_schema_version=1,
            device_network_name=os.getenv("DEVICE_NETWORK_NAME", "greenhouse_iot_net"),
            manager_key=os.getenv("MANAGER_KEY", ""),
            sensor_ip_range=os.getenv("SENSOR_IP_RANGE", "172.28.1.10-172.28.1.250"),
            actuator_ip_range=os.getenv("ACTUATOR_IP_RANGE", "172.28.2.10-172.28.2.250"),
            auto_restart_max_retries=int(os.getenv("AUTO_RESTART_MAX_RETRIES", "5")),
            stop_timeout_seconds=int(os.getenv("STOP_TIMEOUT_SECONDS", "10")),
            device_image=os.getenv("DEVICE_IMAGE", "docker-device-runtime"),
            mqtt_broker_host=os.getenv("MQTT_BROKER_HOST", "mqtt-broker"),
            mqtt_broker_port=os.getenv("MQTT_BROKER_PORT", "1883"),
            mqtt_tls_enabled=os.getenv("MQTT_TLS_ENABLED", "false").strip().lower() == "true",
            mqtt_tls_ca_cert=os.getenv("MQTT_TLS_CA_CERT", "").strip(),
            mqtt_tls_insecure=os.getenv("MQTT_TLS_INSECURE", "false").strip().lower() == "true",
            mqtt_tls_client_cert=os.getenv("MQTT_TLS_CLIENT_CERT", "").strip(),
            mqtt_tls_client_key=os.getenv("MQTT_TLS_CLIENT_KEY", "").strip(),
            mqtt_username_device=os.getenv("MQTT_USERNAME_DEVICE", "").strip(),
            mqtt_password_device=os.getenv("MQTT_PASSWORD_DEVICE", "").strip(),
            mqtt_shared_certs_volume=os.getenv("MQTT_SHARED_CERTS_VOLUME", "").strip(),
            mqtt_certs_rw_dir=os.getenv("MQTT_CERTS_RW_DIR", "/mqtt-certs-rw").strip(),
            mqtt_device_ca_cert_path=os.getenv(
                "MQTT_DEVICE_CA_CERT_PATH", "/mosquitto-config-certs/device-ca.crt"
            ).strip(),
            mqtt_device_ca_key_path=os.getenv(
                "MQTT_DEVICE_CA_KEY_PATH", "/mosquitto-config-certs/device-ca.key"
            ).strip(),
            mqtt_device_certs_subdir=os.getenv("MQTT_DEVICE_CERTS_SUBDIR", "devices").strip() or "devices",
            mqtt_device_crl_path=os.getenv("MQTT_DEVICE_CRL_PATH", "/mqtt-certs-rw/device-ca.crl").strip(),
            mqtt_broker_container_name=os.getenv("MQTT_BROKER_CONTAINER_NAME", "greenhouse_mqtt_broker").strip(),
            runtime_secrets_dir=os.getenv("RUNTIME_SECRETS_DIR", "").strip(),
            device_runtime_secrets_volume=os.getenv("DEVICE_RUNTIME_SECRETS_VOLUME", "").strip(),
            device_group_project=os.getenv("DEVICE_GROUP_PROJECT", "devices"),
            device_group_service=os.getenv("DEVICE_GROUP_SERVICE", "device-runtime"),
        )

    @property
    def orchestration_state_url(self) -> str:
        return f"{self.backend_url}/devices/internal/orchestration-state"

    def to_runtime_config(self) -> DockerRuntimeConfig:
        return DockerRuntimeConfig(
            sensor_ip_range=self.sensor_ip_range,
            actuator_ip_range=self.actuator_ip_range,
            stop_timeout_seconds=self.stop_timeout_seconds,
            auto_restart_max_retries=self.auto_restart_max_retries,
            device_image=self.device_image,
            mqtt_broker_host=self.mqtt_broker_host,
            mqtt_broker_port=self.mqtt_broker_port,
            mqtt_tls_enabled=self.mqtt_tls_enabled,
            mqtt_tls_ca_cert=self.mqtt_tls_ca_cert,
            mqtt_tls_insecure=self.mqtt_tls_insecure,
            mqtt_tls_client_cert=self.mqtt_tls_client_cert,
            mqtt_tls_client_key=self.mqtt_tls_client_key,
            mqtt_username_device=self.mqtt_username_device,
            mqtt_password_device=self.mqtt_password_device,
            backend_url=self.backend_url,
            device_runtime_secrets_volume=self.device_runtime_secrets_volume,
            mqtt_shared_certs_volume=self.mqtt_shared_certs_volume,
            mqtt_device_certs_subdir=self.mqtt_device_certs_subdir,
            runtime_secrets_dir=self.runtime_secrets_dir,
            device_group_project=self.device_group_project,
            device_group_service=self.device_group_service,
        )
