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


def test_botswana_template_uses_seven_three_two_default_pathway():
    template = get_country_template("BW")
    assert template["template_version"] == 2
    assert template["status"] == "starter_requires_authority_review"
    levels = template["levels"]
    codes = [level["code"] for level in levels]
    assert "STANDARD_A" not in codes
    assert "STANDARD_B" not in codes
    assert "FORM_6" not in codes
    assert sum(level["stage"] == "primary" for level in levels) == 7
    assert sum(level["stage"] == "secondary" for level in levels) == 3
    assert sum(level["stage"] == "advanced_secondary" for level in levels) == 2
    assert [level["name"] for level in levels if level["stage"] == "secondary"] == [
        "Form 1", "Form 2", "Form 3"
    ]
    assert [level["name"] for level in levels if level["stage"] == "advanced_secondary"] == [
        "Form 4", "Form 5"
    ]
    assert any("10-year basic/universal education cycle" in note for note in template["notes"])
    assert any("Form 6" in note for note in template["notes"])


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
