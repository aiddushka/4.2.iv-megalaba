from datetime import datetime

from sqlalchemy.orm import Session

from app.models.device_config import DeviceConfig


def upsert_config(
    db: Session,
    device_uid: str,
    config_type: str,
    parameters: dict,
    created_by: int | None = None,
) -> DeviceConfig:
    existing = (
        db.query(DeviceConfig)
        .filter(DeviceConfig.device_uid == device_uid, DeviceConfig.config_type == config_type)
        .first()
    )
    if existing:
        existing.parameters = parameters
        if created_by is not None:
            existing.created_by = created_by
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    cfg = DeviceConfig(
        device_uid=device_uid,
        config_type=config_type,
        parameters=parameters,
        created_by=created_by,
        updated_at=datetime.utcnow(),
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def get_config(db: Session, device_uid: str, config_type: str) -> DeviceConfig | None:
    return (
        db.query(DeviceConfig)
        .filter(DeviceConfig.device_uid == device_uid, DeviceConfig.config_type == config_type)
        .first()
    )

