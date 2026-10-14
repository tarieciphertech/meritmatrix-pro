"""
MeritMatrix Pro 2.0 — FastAPI application entrypoint.

Milestone 1: app bootstrap, configuration, database connectivity, health
check, logging, and centralized error handling.
Milestone 2: users, roles, permissions, authentication, and RBAC.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import configure_logging
from app.routers import (
    academic_years,
    auth,
    class_subjects,
    classes,
    country_configurations,
    enrollments,
    guardian_accounts,
    guardian_portal,
    guardians,
    health,
    schools,
    staff,
    student_guardians,
    students,
    subjects,
    terms,
    users,
)
from app.utils.errors import register_exception_handlers

settings = get_settings()

configure_logging()
logger = logging.getLogger("meritmatrix.main")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Production-ready school administration and academic results management platform.",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # Health and authentication
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)

    # Country templates are read-only reference data; applying one to a
    # school will be handled by a separately authorized setup workflow.
    app.include_router(country_configurations.router)

    # Schools & academic structure
    app.include_router(schools.router)
    app.include_router(academic_years.router)
    app.include_router(terms.router)
    app.include_router(classes.router)
    app.include_router(subjects.router)
    app.include_router(class_subjects.router)

    # People & enrollment
    app.include_router(students.router)
    app.include_router(guardians.router)
    app.include_router(guardian_portal.router)
    app.include_router(guardian_accounts.router)
    app.include_router(student_guardians.router)
    app.include_router(staff.router)
    app.include_router(enrollments.router)

    @app.get("/", tags=["root"])
    def root():
        return {
            "app": settings.APP_NAME,
            "status": "running",
            "docs": f"{settings.API_V1_PREFIX}/docs",
        }

    return app


app = create_app()
