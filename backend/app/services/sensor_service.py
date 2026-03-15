from sqlalchemy.orm import Session

from app.models.sensor_data import SensorData


def create_sensor_data(
    db: Session, device_uid: str, value: float, sensor_type: str | None = None
) -> SensorData:
    data = SensorData(device_uid=device_uid, value=value, sensor_type=sensor_type)
    db.add(data)
    db.commit()
    db.refresh(data)
    return data


def get_all_sensor_data(db: Session) -> list[SensorData]:
    return db.query(SensorData).order_by(SensorData.created_at.desc()).all()

