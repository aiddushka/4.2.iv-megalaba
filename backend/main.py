from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import actuators, auth, automation, devices, sensors, dashboard
from app.database.base import Base
from app.database.session import engine
from app.mqtt.mqtt_manager import MQTTManager
from app.models.device_config import DeviceConfig  # noqa: F401


def create_app() -> FastAPI:
    # создаем таблицы в БД
    Base.metadata.create_all(bind=engine)
    # миграции: добавить новые поля для существующих БД
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS can_view_dashboard BOOLEAN DEFAULT false"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE actuators ADD COLUMN IF NOT EXISTS control_mode VARCHAR(20) DEFAULT 'AUTO'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_secret VARCHAR(255) NOT NULL DEFAULT 'dev_secret'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE sensor_data ADD COLUMN IF NOT EXISTS sensor_type VARCHAR(50)"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS catalog_info TEXT"
                )
            )
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS model_name VARCHAR(120)")
            )
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS manufacturer VARCHAR(120)"
                )
            )
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS min_value FLOAT")
            )
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS max_value FLOAT")
            )
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS config_settings JSON")
            )
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS is_configured BOOLEAN DEFAULT false")
            )
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL")
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

    # MQTT менеджер запускается в фоне и обеспечивает приём телеметрии от устройств.
    mqtt_manager = MQTTManager()
    app.state.mqtt_manager = mqtt_manager

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

    @app.on_event("startup")
    def _startup() -> None:
        mqtt_manager.start()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        mqtt_manager.stop()

    @app.get("/")
    def root():
        return {"message": "IoT Greenhouse API running"}

    return app


app = create_app()
