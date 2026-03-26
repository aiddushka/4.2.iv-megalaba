from sqlalchemy import Column, Integer, String

from app.database.base import Base


class Actuator(Base):
    __tablename__ = "actuators"

    id = Column(Integer, primary_key=True, index=True)
    device_uid = Column(String(100), unique=True, index=True, nullable=False)
    actuator_type = Column(
        String(50), nullable=False
    )  # irrigation, heater, ventilation, light
    state = Column(String(20), default="OFF")  # ON | OFF | etc.
    # Режим управления: AUTO (автоматика) или MANUAL (ручное управление с дашборда)
    control_mode = Column(String(20), default="AUTO")

