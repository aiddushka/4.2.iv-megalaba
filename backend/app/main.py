from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from pathlib import Path

from app.api import actuators, auth, automation, devices, sensors, dashboard
from app.database.base import Base
from app.database.session import engine
from app.services import mqtt_service


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS controller VARCHAR(100)")
            )
            conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS pin INTEGER"))
            conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS bus VARCHAR(50)"))
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS bus_address VARCHAR(100)")
            )
            conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS components JSON"))
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS accepts_data BOOLEAN NOT NULL DEFAULT TRUE"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_maintenance TIMESTAMP"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS maintenance_notes VARCHAR(512)"
                )
            )
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS change_history JSON")
            )
            conn.execute(
                text("ALTER TABLE devices ALTER COLUMN status SET DEFAULT 'active'")
            )
    except Exception:
        pass

    app = FastAPI(title="IoT Greenhouse API")
    backend_root = Path(__file__).resolve().parent.parent
    images_dir = backend_root / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/images", StaticFiles(directory=str(images_dir)), name="images")

    app.include_router(auth.router)
    app.include_router(devices.router)
    app.include_router(sensors.router)
    app.include_router(actuators.router)
    app.include_router(automation.router)
    app.include_router(dashboard.router)

    @app.get("/")
    def root():
        return {"message": "IoT Greenhouse API running"}

    @app.on_event("startup")
    def startup_mqtt_listener():
        mqtt_service.start_mqtt_listener()

    @app.on_event("shutdown")
    def shutdown_mqtt_listener():
        mqtt_service.stop_mqtt_listener()

    return app


app = create_app()

