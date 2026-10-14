"""Read-only country education configuration endpoints.

Templates are public reference data. Applying a template to a school is a
separate authenticated workflow and is intentionally not implemented here.
"""
from fastapi import APIRouter, HTTPException

from app.services.country_templates import get_country_template, list_country_templates

router = APIRouter(prefix="/api/v1/country-configurations", tags=["country-configurations"])


@router.get("")
def list_configurations():
    """List supported country templates and their review status."""
    return list_country_templates()


@router.get("/{country_code}")
def read_configuration(country_code: str):
    """Read a country template by ISO alpha-2 country code (ZW, BW)."""
    template = get_country_template(country_code)
    if template is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "COUNTRY_TEMPLATE_NOT_FOUND",
                "message": "No education template is configured for that country.",
            },
        )
    return template
