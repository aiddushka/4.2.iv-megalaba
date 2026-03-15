from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.base import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_uid = Column(String(100), unique=True, index=True, nullable=False)
    device_type = Column(String(50), nullable=False)  # CONTROLLER, SENSOR, ACTUATOR
    description = Column(String(255), nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    location = Column(String(255), nullable=True)
    status = Column(
        String(50), default="registered"
    )  # registered | unassigned | assigned

    owner = relationship("User", backref="devices")

from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from app.database.session import Base
from datetime import datetime

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_uid = Column(String(100), unique=True, index=True)
    type = Column(String(50))
    name = Column(String(100))
    status = Column(String(50), default="offline")
    configured = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)