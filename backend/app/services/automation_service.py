from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.device_link import DeviceLink
from app.models.automation_rule import AutomationRule
from app.models.sensor_data import SensorData

UNSET = object()


def _sensor_domain(device_type: str) -> str | None:
    normalized = (device_type or "").upper()
    if "TEMP" in normalized:
        return "temperature"
    if "HUMIDITY_SOIL" in normalized or ("SOIL" in normalized and "HUMIDITY" in normalized):
        return "soil_humidity"
    if "HUMIDITY_AIR" in normalized or ("AIR" in normalized and "HUMIDITY" in normalized):
        return "air_humidity"
    if "LIGHT" in normalized:
        return "light"
    return None


def _actuator_domain(device_type: str) -> str | None:
    normalized = (device_type or "").upper()
    if "HEATER" in normalized or "TEMP" in normalized:
        return "temperature"
    if "VENT" in normalized:
        return "air_humidity"
    if "IRRIG" in normalized:
        return "soil_humidity"
    if "LIGHT" in normalized:
        return "light"
    return None


def _sensor_display_name(device_type: str) -> str:
    domain = _sensor_domain(device_type)
    if domain == "temperature":
        return "датчик температуры"
    if domain == "soil_humidity":
        return "датчик влажности почвы"
    if domain == "air_humidity":
        return "датчик влажности воздуха"
    if domain == "light":
        return "датчик освещенности"
    return f"датчик ({device_type})"


def _actuator_display_name(device_type: str) -> str:
    domain = _actuator_domain(device_type)
    if domain == "temperature":
        return "актуатор температуры"
    if domain == "soil_humidity":
        return "актуатор полива"
    if domain == "air_humidity":
        return "актуатор вентиляции"
    if domain == "light":
        return "актуатор освещения"
    return f"актуатор ({device_type})"


def _expected_sensor_for_actuator(device_type: str) -> str:
    domain = _actuator_domain(device_type)
    if domain == "temperature":
        return "датчик температуры"
    if domain == "soil_humidity":
        return "датчик влажности почвы"
    if domain == "air_humidity":
        return "датчик влажности воздуха"
    if domain == "light":
        return "датчик освещенности"
    return "совместимый датчик"


def are_devices_compatible(source_type: str, target_type: str) -> bool:
    sensor_domain = _sensor_domain(source_type)
    actuator_domain = _actuator_domain(target_type)
    return bool(sensor_domain and actuator_domain and sensor_domain == actuator_domain)


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
    source_device = db.query(Device).filter(Device.device_uid == source_device_uid).first()
    if not source_device:
        raise LookupError(f"Source device '{source_device_uid}' not found")
    target_device = db.query(Device).filter(Device.device_uid == target_device_uid).first()
    if not target_device:
        raise LookupError(f"Target device '{target_device_uid}' not found")

    if "SENSOR" not in (source_device.device_type or ""):
        raise ValueError("Source device must be a sensor")
    if "ACTUATOR" not in (target_device.device_type or ""):
        raise ValueError("Target device must be an actuator")
    if not are_devices_compatible(source_device.device_type, target_device.device_type):
        source_name = _sensor_display_name(source_device.device_type or "")
        actuator_name = _actuator_display_name(target_device.device_type or "")
        expected_sensor = _expected_sensor_for_actuator(target_device.device_type or "")
        raise ValueError(
            f"Несовместимая связь: {source_name} не может быть связан с {actuator_name}. "
            f"Для {actuator_name} нужен {expected_sensor}."
        )

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

