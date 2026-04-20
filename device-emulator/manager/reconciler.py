import json
from pathlib import Path

from manager import naming
from manager.docker_runtime import DockerRuntimeManager
from manager.orchestration_api import OrchestrationApiClient


class DeviceReconciler:
    def __init__(
        self,
        runtime_manager: DockerRuntimeManager,
        orchestration_api: OrchestrationApiClient,
        runtime_secrets_dir: str,
    ) -> None:
        self.runtime_manager = runtime_manager
        self.orchestration_api = orchestration_api
        self.runtime_secrets_dir = runtime_secrets_dir

    def _sync_runtime_secret_file(
        self,
        device_uid: str,
        device_token: str | None,
        device_token_version: int | None,
        info: dict,
    ) -> None:
        if not self.runtime_secrets_dir:
            return
        ver = int(device_token_version if device_token_version is not None else 0)
        if device_token is None:
            info["observed_device_token_version"] = ver
            return
        tok = device_token
        if info.get("synced_device_token_version") == ver and info.get("synced_device_token") == tok:
            return
        base = Path(self.runtime_secrets_dir)
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"{naming.device_secret_basename(device_uid)}.json"
        tmp = path.parent / f"{path.name}.tmp"
        payload = {"device_token": tok, "device_token_version": ver}
        tmp.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        tmp.replace(path)
        info["synced_device_token_version"] = ver
        info["synced_device_token"] = tok
        print(f"[manager] runtime secret file updated for {device_uid} version={ver}")

    def reconcile_device(self, client, network, state: dict, desired: dict) -> None:
        device_uid = desired.get("device_uid")
        device_type = desired.get("device_type")
        desired_runtime_state = desired.get("desired_runtime_state", "stopped")
        token_is_present = "device_token" in desired
        device_token = desired.get("device_token") if token_is_present else None
        device_token_version = desired.get("device_token_version")
        if not device_uid or not device_type:
            return

        if desired_runtime_state == "removed":
            self.runtime_manager.ensure_removed(client, state, device_uid)
            return

        info = state["devices"].setdefault(device_uid, {})
        desired_ver = int(device_token_version) if device_token_version is not None else None
        synced_ver = (
            int(info.get("synced_device_token_version"))
            if info.get("synced_device_token_version") is not None
            else None
        )
        needs_token_sync = (desired_ver is not None and desired_ver != synced_ver) or not info.get(
            "synced_device_token"
        )
        if not token_is_present and needs_token_sync:
            fetched_token, fetched_ver = self.orchestration_api.fetch_runtime_token(device_uid)
            if fetched_token:
                device_token = fetched_token
                token_is_present = True
            if fetched_ver is not None:
                device_token_version = fetched_ver

        container, info = self.runtime_manager.ensure_created(
            client, network, state, device_uid, device_type, device_token
        )
        self._sync_runtime_secret_file(device_uid, device_token, device_token_version, info)
        info["desired_runtime_state"] = desired_runtime_state
        info["status"] = desired.get("status", info.get("status"))

        if desired_runtime_state == "running":
            self.runtime_manager.ensure_running(container, info)
        else:
            self.runtime_manager.ensure_stopped(container, info)
