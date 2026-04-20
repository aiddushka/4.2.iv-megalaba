import requests


class OrchestrationApiClient:
    def __init__(self, backend_url: str, manager_key: str = "", timeout_seconds: int = 5) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.manager_key = manager_key
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"X-Manager-Key": self.manager_key} if self.manager_key else {}

    def fetch_orchestration_state(self) -> list[dict] | None:
        try:
            response = requests.get(
                f"{self.backend_url}/devices/internal/orchestration-state",
                timeout=self.timeout_seconds,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
        except Exception as exc:
            print(f"[manager] failed to fetch orchestration state: {exc}")
        return None

    def fetch_runtime_token(self, device_uid: str) -> tuple[str | None, int | None]:
        try:
            response = requests.get(
                f"{self.backend_url}/devices/internal/runtime-token/{device_uid}",
                timeout=self.timeout_seconds,
                headers=self._headers(),
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                tok = payload.get("device_token")
                ver = payload.get("device_token_version")
                token_value = tok if isinstance(tok, str) else None
                token_ver = int(ver) if ver is not None else None
                return token_value, token_ver
        except Exception as exc:
            print(f"[manager] failed to fetch runtime token for {device_uid}: {exc}")
        return None, None
