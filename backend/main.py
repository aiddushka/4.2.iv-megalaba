from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import actuators, auth, automation, devices, sensors, dashboard
from app.database.base import Base
from app.database.session import engine


def create_app() -> FastAPI:
    # создаем таблицы в БД
    Base.metadata.create_all(bind=engine)
    # миграция: добавить can_view_dashboard для существующих БД
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS can_view_dashboard BOOLEAN DEFAULT false"
                )
            )
    except Exception:
        pass

    # Учётная запись админа по умолчанию (admin / 123)
    try:
        from app.database.session import SessionLocal
        from app.models.user import User
        from app.services import auth_service

        db = SessionLocal()
        try:
            if db.query(User).filter(User.username == "admin").first() is None:
                auth_service.create_user(db, "admin", "123", is_admin=True)
        finally:
            db.close()
    except Exception:
        pass

    app = FastAPI(title="IoT Greenhouse API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # подключаем все роутеры
    app.include_router(auth.router)
    app.include_router(devices.router)
    app.include_router(sensors.router)
    app.include_router(actuators.router)
    app.include_router(automation.router)
    app.include_router(dashboard.router)

    @app.get("/")
    def root():
        return {"message": "IoT Greenhouse API running"}

    return app


app = create_app()
