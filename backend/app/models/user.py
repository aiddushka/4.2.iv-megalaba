from sqlalchemy import Boolean, Column, Integer, String

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    # для работников: разрешён ли просмотр дашборда (админ всегда может)
    can_view_dashboard = Column(Boolean, default=False)

