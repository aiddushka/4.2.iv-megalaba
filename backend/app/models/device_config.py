from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String

from app.database.base import Base


class DeviceConfig(Base):
    __tablename__ = "device_configs"

    id = Column(Integer, primary_key=True, index=True)
    device_uid = Column(String(100), index=True, nullable=False)
    config_type = Column(String(50), nullable=False)  # threshold|calibration|schedule
    parameters = Column(JSON, nullable=False, default=dict)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

