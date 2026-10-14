"""Country education starter-template tests."""
from app.services.country_templates import get_country_template, list_country_templates


def test_supported_country_templates_are_present():
    templates = {item["country_code"]: item for item in list_country_templates()}
    assert {"ZW", "BW"} <= set(templates)
    assert templates["ZW"]["country_name"] == "Zimbabwe"
    assert templates["BW"]["country_name"] == "Botswana"


def test_zimbabwe_template_contains_expected_levels():
    template = get_country_template("zw")
    codes = {level["code"] for level in template["levels"]}
    assert {"ECD_A", "ECD_B", "GRADE_1", "GRADE_7", "FORM_1", "FORM_4", "FORM_5", "FORM_6"} <= codes


def test_botswana_template_is_explicitly_draft():
    template = get_country_template("BW")
    assert template["status"] == "draft_requires_authority_review"
    assert any(level.get("requires_review") for level in template["levels"])


def test_calendar_event_types_are_distinct():
    expected = {"public_holiday", "school_holiday", "exam_period", "school_closure"}
    for template in list_country_templates():
        assert expected <= set(template["calendar_event_types"])


def test_unknown_country_returns_none():
    assert get_country_template("XX") is None


def test_template_results_are_copies():
    first = get_country_template("ZW")
    first["levels"].clear()
    assert get_country_template("ZW")["levels"]
