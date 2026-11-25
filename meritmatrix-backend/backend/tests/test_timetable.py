"""Timetable input validation and authentication regression tests."""
from datetime import date, time
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.timetable import TimetableEntryCreate


def _payload(**overrides):
    values = {
        "staff_id": uuid4(),
        "class_subject_id": uuid4(),
        "weekday": 0,
        "start_time": time(8, 0),
        "end_time": time(8, 40),
        "effective_from": date(2026, 1, 1),
    }
    values.update(overrides)
    return values


def test_timetable_entry_accepts_valid_weekly_slot():
    entry = TimetableEntryCreate(**_payload())
    assert entry.weekday == 0
    assert entry.start_time == time(8, 0)
    assert entry.end_time == time(8, 40)


@pytest.mark.parametrize("weekday", [-1, 7])
def test_timetable_entry_rejects_invalid_weekday(weekday):
    with pytest.raises(ValidationError):
        TimetableEntryCreate(**_payload(weekday=weekday))


def test_timetable_entry_rejects_end_before_start():
    with pytest.raises(ValidationError):
        TimetableEntryCreate(**_payload(start_time=time(9, 0), end_time=time(8, 0)))


def test_timetable_entry_rejects_zero_length_lesson():
    with pytest.raises(ValidationError):
        TimetableEntryCreate(**_payload(start_time=time(8, 0), end_time=time(8, 0)))


def test_timetable_entry_rejects_end_date_before_start_date():
    with pytest.raises(ValidationError):
        TimetableEntryCreate(**_payload(effective_to=date(2025, 12, 31)))


def test_timetable_list_requires_authentication(client):
    response = client.get(f"/api/v1/timetable?school_id={uuid4()}")
    assert response.status_code == 401
