from pydantic import ValidationError
import pytest

from app.schemas.school import SchoolCreate


def test_school_logo_accepts_small_png_data_url():
    logo = "data:image/png;base64," + ("A" * 100)
    payload = SchoolCreate(name="Logo School", code="LOGO201", logo_url=logo)
    assert payload.logo_url == logo


def test_school_logo_rejects_other_data_mime_types():
    with pytest.raises(ValidationError):
        SchoolCreate(name="Bad Logo", code="LOGO202", logo_url="data:text/plain;base64,SGVsbG8=")


def test_school_logo_rejects_oversized_data_url():
    with pytest.raises(ValidationError):
        SchoolCreate(name="Large Logo", code="LOGO203", logo_url="data:image/png;base64," + ("A" * 360001))
