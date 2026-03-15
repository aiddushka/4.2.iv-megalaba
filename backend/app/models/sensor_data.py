from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database.base import Base


class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    device_uid = Column(String(100), index=True, nullable=False)
    sensor_type = Column(String(50), nullable=True)  # temperature, humidity, etc.
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)