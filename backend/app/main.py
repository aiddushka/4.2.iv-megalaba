from fastapi import FastAPI

from app.api import actuators, auth, automation, devices, sensors, dashboard
from app.database.base import Base
from app.database.session import engine


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title="IoT Greenhouse API")

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

