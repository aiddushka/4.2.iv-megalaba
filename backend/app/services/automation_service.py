from sqlalchemy.orm import Session

from app.models.automation_rule import AutomationRule
from app.models.sensor_data import SensorData


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

