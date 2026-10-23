"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from backend.database import Base, engine
from backend import models  # noqa: F401 - registers model metadata before create_all
from backend.routers.issues import router as issues_router


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Registering models above ensures every table is present before serving requests.
        Base.metadata.create_all(bind=engine)
        # create_all does not alter existing tables, so add this nullable field for
        # existing installations while preserving their issue records.
        columns = {column["name"] for column in inspect(engine).get_columns("support_issues")}
        if "assigned_engineer" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE support_issues ADD COLUMN assigned_engineer VARCHAR(200)")
                )
        yield

    app = FastAPI(title="Support Issue Management System", version="1.0.0", lifespan=lifespan)
    origins = [origin.strip() for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(issues_router)

    @app.get("/api/health", tags=["health"])
    def health_check():
        return {"status": "ok"}

    return app


app = create_app()
