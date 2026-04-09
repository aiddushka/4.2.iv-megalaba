from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.database.base import Base


class DeviceLink(Base):
    __tablename__ = "device_links"

    id = Column(Integer, primary_key=True, index=True)
    source_device_uid = Column(String(100), nullable=False, index=True)
    target_device_uid = Column(String(100), nullable=False, index=True)
    controller = Column(String(100), nullable=True)
    description = Column(String(255), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    auto_control_enabled = Column(Boolean, nullable=False, default=False)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
