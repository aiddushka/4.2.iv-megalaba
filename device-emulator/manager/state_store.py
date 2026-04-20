import json
from pathlib import Path
from typing import Callable


def load_state(state_file_path: Path, schema_version: int, now_iso: Callable[[], str]) -> dict:
    if not state_file_path.exists():
        return {
            "schema_version": schema_version,
            "updated_at": now_iso(),
            "devices": {},
        }
    try:
        payload = json.loads(state_file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("State file is not an object")
        payload.setdefault("schema_version", schema_version)
        payload.setdefault("updated_at", now_iso())
        payload.setdefault("devices", {})
        if not isinstance(payload["devices"], dict):
            payload["devices"] = {}
        return payload
    except Exception as exc:
        print(f"[manager] state load failed, fallback to empty state: {exc}")
        return {
            "schema_version": schema_version,
            "updated_at": now_iso(),
            "devices": {},
        }


def save_state(state_file_path: Path, state: dict, schema_version: int, now_iso: Callable[[], str]) -> None:
    state["schema_version"] = schema_version
    state["updated_at"] = now_iso()
    state_file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_file_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")
    temp_path.replace(state_file_path)
