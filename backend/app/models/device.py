from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.database.base import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_uid = Column(String(100), unique=True, index=True, nullable=False)
    device_type = Column(String(50), nullable=False)  # CONTROLLER, SENSOR, ACTUATOR
    description = Column(String(255), nullable=True)
    controller = Column(String(100), nullable=True)
    pin = Column(Integer, nullable=True)
    bus = Column(String(50), nullable=True)
    bus_address = Column(String(100), nullable=True)
    components = Column(JSON, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    location = Column(String(255), nullable=True)
    status = Column(String(50), default="active")
    accepts_data = Column(Boolean, nullable=False, default=True)
    device_token_hash = Column(String(128), nullable=True)
    device_token_version = Column(Integer, nullable=False, default=1)
    device_token_revoked_at = Column(DateTime, nullable=True)
    last_maintenance = Column(DateTime, nullable=True)
    maintenance_notes = Column(String(512), nullable=True)
    change_history = Column(JSON, nullable=True)

    owner = relationship("User", backref="devices")