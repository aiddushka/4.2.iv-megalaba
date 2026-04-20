import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.device import Device

RUNTIME_TOKEN_STORE_DIR = Path(os.getenv("RUNTIME_TOKEN_STORE_DIR", "/runtime-token-store")).resolve()


def generate_device_token() -> str:
    # 256-bit-ish token, URL-safe
    return secrets.token_urlsafe(32)


def hash_device_token(token: str, pepper: str) -> str:
    material = (pepper or "") + ":" + (token or "")
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _runtime_token_path(device_uid: str) -> Path:
    safe_uid = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in device_uid)
    return RUNTIME_TOKEN_STORE_DIR / f"{safe_uid}.json"


def _persist_runtime_token(device_uid: str, token: str, version: int) -> None:
    RUNTIME_TOKEN_STORE_DIR.mkdir(parents=True, exist_ok=True)
    path = _runtime_token_path(device_uid)
    tmp = path.parent / f"{path.name}.tmp"
    payload = {"device_uid": device_uid, "device_token": token, "device_token_version": int(version)}
    tmp.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    tmp.replace(path)


def _remove_runtime_token(device_uid: str) -> None:
    try:
        path = _runtime_token_path(device_uid)
        if path.is_file():
            path.unlink()
    except OSError:
        pass


def _read_runtime_token(device_uid: str) -> tuple[str | None, int | None]:
    path = _runtime_token_path(device_uid)
    if not path.is_file():
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        token = payload.get("device_token")
        version = payload.get("device_token_version")
        token_value = token if isinstance(token, str) and token else None
        version_value = int(version) if version is not None else None
        return token_value, version_value
    except Exception:
        return None, None


def get_runtime_token_for_device(device: Device) -> tuple[str | None, int]:
    token, version_from_file = _read_runtime_token(device.device_uid)
    db_version = int(getattr(device, "device_token_version", 1) or 1)
    if token:
        return token, int(version_from_file if version_from_file is not None else db_version)
    return None, db_version


def set_device_token(db: Session, device: Device, token: str, pepper: str) -> None:
    device.device_token_hash = hash_device_token(token, pepper)
    device.device_token_revoked_at = None
    device.device_token_version = int(getattr(device, "device_token_version", 0) or 0) + 1
    db.commit()
    db.refresh(device)
    _persist_runtime_token(device.device_uid, token, int(device.device_token_version or 1))


def verify_device_token(device: Device | None, token: str | None, pepper: str) -> bool:
    if device is None:
        return False
    if getattr(device, "device_token_revoked_at", None) is not None:
        return False
    expected_hash = getattr(device, "device_token_hash", None)
    if not expected_hash:
        return False
    if not token:
        return False
    actual_hash = hash_device_token(token, pepper)
    return hmac.compare_digest(str(expected_hash), str(actual_hash))


def revoke_device_token(db: Session, device: Device) -> None:
    device.device_token_revoked_at = datetime.utcnow()
    db.commit()
    db.refresh(device)
    _remove_runtime_token(device.device_uid)

