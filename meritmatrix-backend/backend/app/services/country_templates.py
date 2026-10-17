"""Versioned starter education templates by country.

Templates are configurable defaults, not automatic changes to existing school
records. Country-specific rules and dates must be reviewed before production use.
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
        "institution_types": ["primary", "secondary", "high_school", "combined", "tertiary"],
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
        "template_version": 2,
        "status": "starter_requires_authority_review",
        "timezone": "Africa/Gaborone",
        "currency": "BWP",
        "institution_types": ["early_childhood", "primary", "secondary", "high_school", "combined", "tertiary"],
        "levels": [
            {"code": "PRE_PRIMARY", "name": "Pre-primary / Early Childhood (optional)", "stage": "early_childhood", "sequence": 10},
            *[
                {"code": f"STANDARD_{n}", "name": f"Standard {n}", "stage": "primary", "sequence": 100 + n * 10}
                for n in range(1, 8)
            ],
            *[
                {"code": f"FORM_{n}", "name": f"Form {n}", "stage": "secondary", "sequence": 200 + n * 10}
                for n in range(1, 4)
            ],
            *[
                {"code": f"FORM_{n}", "name": f"Form {n}", "stage": "advanced_secondary", "sequence": 230 + n * 10}
                for n in range(4, 7)
            ],
        ],
        "calendar_event_types": [
            "public_holiday", "school_holiday", "exam_period", "school_closure"
        ],
        "notes": [
            "The default school pathway is 7 years of primary (Standard 1–7), 3 years of junior secondary (Forms 1–3), and 2 years of senior secondary (Forms 4–5).",
            "Forms 1–3 complete the 10-year basic/universal education cycle; the full 7-3-2 pathway spans 12 school years.",
            "Pre-primary is optional and separate from the 7-3-2 sequence. Tertiary and vocational structures must be configured separately.",
            "Form 6 is included as an optional school-specific high-school extension and requires local authority confirmation before official use.",
            "Verify current official level labels and examination pathways before production activation. Calendar dates must be approved for each academic year."
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
