"""Health check endpoint used for liveness/readiness probes."""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """
    Returns application status and confirms database connectivity.

    Response shape:
        {
          "status": "ok" | "degraded",
          "app": "MeritMatrix Pro 2.0",
          "environment": "development",
          "database": "connected" | "unreachable"
        }
    """
    settings = get_settings()
    db_ok = check_database_connection()

    body = {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_ok else "unreachable",
    }

    status_code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=body)
