"""
MeritMatrix Pro 2.0 — FastAPI application entrypoint.

Milestone 1: app bootstrap, configuration, database connectivity, health
check, logging, and centralized error handling.
Milestone 2: users, roles, permissions, authentication, and RBAC.
Domain routers (students, classes, assessments, etc.) are added in
later milestones.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import configure_logging
from app.routers import academic_years, auth, class_subjects, classes, enrollments, guardians, health, schools, staff, student_guardians, students, subjects, terms, users
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

    # Root-level health check (unversioned, for load balancers / uptime probes)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    # Milestone 3: Schools & Academic Structure
    app.include_router(schools.router)
    app.include_router(academic_years.router)
    app.include_router(terms.router)
    app.include_router(classes.router)
    app.include_router(subjects.router)
    app.include_router(class_subjects.router)
    # Milestone 4: People & Enrollment
    app.include_router(students.router)
    app.include_router(guardians.router)
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
