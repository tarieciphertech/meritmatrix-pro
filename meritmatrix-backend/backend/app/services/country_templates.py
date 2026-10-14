"""Versioned starter education templates by country.

These are configuration defaults, not legal assertions. Botswana's exact
level labels and examination pathways remain marked for administrative
verification before being activated for production school setup.
"""
from copy import deepcopy

COUNTRY_TEMPLATES = {
    "ZW": {
        "country_code": "ZW",
        "country_name": "Zimbabwe",
        "template_version": 1,
        "status": "starter",
        "timezone": "Africa/Harare",
        "currency": "USD",
        "institution_types": ["primary", "secondary", "combined", "tertiary"],
        "levels": [
            {"code": "ECD_A", "name": "ECD A", "stage": "early_childhood", "sequence": 10},
            {"code": "ECD_B", "name": "ECD B", "stage": "early_childhood", "sequence": 20},
            *[
                {"code": f"GRADE_{n}", "name": f"Grade {n}", "stage": "primary", "sequence": 100 + n * 10}
                for n in range(1, 8)
            ],
            *[
                {"code": f"FORM_{n}", "name": f"Form {n}", "stage": "secondary", "sequence": 200 + n * 10}
                for n in range(1, 5)
            ],
            *[
                {"code": f"FORM_{n}", "name": f"Form {n}", "stage": "advanced_secondary", "sequence": 250 + n * 10}
                for n in range(5, 7)
            ],
        ],
        "calendar_event_types": [
            "public_holiday", "school_holiday", "exam_period", "school_closure"
        ],
        "notes": [
            "School-specific offerings must be selected during setup.",
            "Tertiary programmes require a separate configurable structure.",
            "Calendar dates and exam rules must be reviewed for each academic year."
        ],
    },
    "BW": {
        "country_code": "BW",
        "country_name": "Botswana",
        "template_version": 1,
        "status": "draft_requires_authority_review",
        "timezone": "Africa/Gaborone",
        "currency": "BWP",
        "institution_types": ["primary", "secondary", "combined", "tertiary"],
        "levels": [
            {"code": "KINDERGARTEN", "name": "Kindergarten / Early Childhood", "stage": "early_childhood", "sequence": 10},
            {"code": "STANDARD_A", "name": "Standard A", "stage": "primary", "sequence": 20, "requires_review": True},
            {"code": "STANDARD_B", "name": "Standard B", "stage": "primary", "sequence": 30, "requires_review": True},
            *[
                {"code": f"STANDARD_{n}", "name": f"Standard {n}", "stage": "primary", "sequence": 100 + n * 10, "requires_review": True}
                for n in range(1, 8)
            ],
            *[
                {"code": f"FORM_{n}", "name": f"Form {n}", "stage": "secondary", "sequence": 200 + n * 10, "requires_review": True}
                for n in range(1, 6)
            ],
        ],
        "calendar_event_types": [
            "public_holiday", "school_holiday", "exam_period", "school_closure"
        ],
        "notes": [
            "Draft template only: verify official level names and examination pathways before production activation.",
            "Do not infer that every institution offers every listed level.",
            "Calendar dates must be approved for each academic year; public holidays, school holidays, examinations, and school-specific closures are separate event types."
        ],
    },
}


def list_country_templates():
    """Return detached copies so API callers cannot mutate the module defaults."""
    return [deepcopy(COUNTRY_TEMPLATES[code]) for code in sorted(COUNTRY_TEMPLATES)]


def get_country_template(country_code: str):
    """Return a detached template by ISO alpha-2 code, or None if unsupported."""
    template = COUNTRY_TEMPLATES.get(country_code.strip().upper())
    return deepcopy(template) if template else None
