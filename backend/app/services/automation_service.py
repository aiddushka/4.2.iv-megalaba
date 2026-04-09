from sqlalchemy.orm import Session

from app.models.device_link import DeviceLink
from app.models.automation_rule import AutomationRule
from app.models.sensor_data import SensorData

UNSET = object()


def create_rule(
    db: Session,
    name: str,
    sensor_type: str,
    condition: str,
    threshold: str,
    actuator_type: str,
    action: str,
) -> AutomationRule:
    rule = AutomationRule(
        name=name,
        sensor_type=sensor_type,
        condition=condition,
        threshold=threshold,
        actuator_type=actuator_type,
        action=action,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def get_rules(db: Session) -> list[AutomationRule]:
    return db.query(AutomationRule).all()


def evaluate_rules_for_sensor(db: Session, sensor_data: SensorData) -> list[AutomationRule]:
    """Простая заглушка: сейчас просто возвращаем все правила по типу сенсора."""
    return db.query(AutomationRule).filter(
        AutomationRule.sensor_type == (sensor_data.sensor_type or "")
    ).all()


def create_device_link(
    db: Session,
    source_device_uid: str,
    target_device_uid: str,
    controller: str | None = None,
    description: str | None = None,
    active: bool = True,
    auto_control_enabled: bool = False,
    min_value: float | None = None,
    max_value: float | None = None,
) -> DeviceLink:
    link = DeviceLink(
        source_device_uid=source_device_uid,
        target_device_uid=target_device_uid,
        controller=controller,
        description=description,
        active=active,
        auto_control_enabled=auto_control_enabled,
        min_value=min_value,
        max_value=max_value,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def get_device_links(db: Session, device_uid: str | None = None) -> list[DeviceLink]:
    query = db.query(DeviceLink)
    if device_uid:
        query = query.filter(
            (DeviceLink.source_device_uid == device_uid)
            | (DeviceLink.target_device_uid == device_uid)
        )
    return query.order_by(DeviceLink.id.desc()).all()


def delete_device_link(db: Session, link_id: int) -> bool:
    link = db.query(DeviceLink).filter(DeviceLink.id == link_id).first()
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True


def update_device_link(
    db: Session,
    link_id: int,
    auto_control_enabled: bool | None | object = UNSET,
    min_value: float | None | object = UNSET,
    max_value: float | None | object = UNSET,
    description: str | None | object = UNSET,
) -> DeviceLink | None:
    link = db.query(DeviceLink).filter(DeviceLink.id == link_id).first()
    if not link:
        return None
    if auto_control_enabled is not UNSET:
        link.auto_control_enabled = auto_control_enabled
    if min_value is not UNSET:
        link.min_value = min_value
    if max_value is not UNSET:
        link.max_value = max_value
    if description is not UNSET:
        link.description = description
    db.commit()
    db.refresh(link)
    return link

