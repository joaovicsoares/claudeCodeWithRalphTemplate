from fastapi import FastAPI

from app.routers import health, ralph


def create_app() -> FastAPI:
    app = FastAPI(title="Ralph Runner API", version="1.1.0")
    app.include_router(health.router)
    app.include_router(ralph.router)
    return app


app = create_app()
