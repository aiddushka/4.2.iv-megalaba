from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database.base import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_uid = Column(String(100), unique=True, index=True, nullable=False)
    device_type = Column(String(50), nullable=False)  # CONTROLLER, SENSOR, ACTUATOR
    description = Column(String(255), nullable=True)

    # Полное описание устройства (справочник/паспорт/инструкция).
    # Отображается на дашборде с возможностью раскрытия.
    catalog_info = Column(Text, nullable=True)

    # Секрет используется устройством для HMAC-подписи сообщений в MQTT.
    # В рамках учебной/демо-системы хранится в открытом виде (чтобы устройство могло
    # подписывать payload, а backend мог проверять подпись).
    device_secret = Column(String(255), nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    location = Column(String(255), nullable=True)

    # Паспортные данные устройства (устанавливает администратор)
    model_name = Column(String(120), nullable=True)
    manufacturer = Column(String(120), nullable=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    config_settings = Column(JSON, nullable=True)  # доп. настройки в JSON
    is_configured = Column(Boolean, default=False, nullable=False)

    # Мягкое удаление: если deleted_at заполнено, устройство выключено из системы
    deleted_at = Column(DateTime, nullable=True)

    status = Column(
        String(50), default="registered"
    )  # registered | unassigned | assigned | deleted

    owner = relationship("User", backref="devices")