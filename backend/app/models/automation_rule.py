from sqlalchemy import Column, Integer, String

from app.database.base import Base


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)

    sensor_type = Column(String(50), nullable=False)
    condition = Column(String(10), nullable=False)  # >, <, >=, <=
    threshold = Column(String(50), nullable=False)  # храним как строку для простоты

    actuator_type = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)  # ON, OFF, и т.п.

