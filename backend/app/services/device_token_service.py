import hashlib
import hmac
import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.device import Device


def generate_device_token() -> str:
    # 256-bit-ish token, URL-safe
    return secrets.token_urlsafe(32)


def hash_device_token(token: str, pepper: str) -> str:
    material = (pepper or "") + ":" + (token or "")
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def set_device_token(db: Session, device: Device, token: str, pepper: str) -> None:
    device.device_token = token
    device.device_token_hash = hash_device_token(token, pepper)
    device.device_token_revoked_at = None
    device.device_token_version = int(getattr(device, "device_token_version", 0) or 0) + 1
    db.commit()
    db.refresh(device)


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

