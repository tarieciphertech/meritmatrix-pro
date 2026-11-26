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


def test_timetable_is_school_scoped_assignment_scoped_and_rejects_overlaps(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    from app.models.academic_year import AcademicYear
    from app.models.class_subject import ClassSubject
    from app.models.clazz import Class
    from app.models.school import School
    from app.models.staff import Staff
    from app.models.subject import Subject
    from app.models.teaching_assignment import TeachingAssignment
    from app.models.user_school import UserSchool

    today = date.today()
    school = School(name="Timetable School", code="TMT001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    academic_year = AcademicYear(
        school_id=school.id, name="Test Academic Year",
        start_date=today.replace(month=1, day=1), end_date=today.replace(month=12, day=31),
        is_current=True, is_active=True,
    )
    db_session.add(academic_year)
    db_session.flush()

    class_one = Class(school_id=school.id, name="Form 1A", code="F1A", level=1, is_active=True)
    class_two = Class(school_id=school.id, name="Form 1B", code="F1B", level=1, is_active=True)
    class_three = Class(school_id=school.id, name="Form 1C", code="F1C", level=1, is_active=True)
    subject_one = Subject(school_id=school.id, name="Mathematics", code="MATH", is_active=True)
    subject_two = Subject(school_id=school.id, name="English", code="ENG", is_active=True)
    db_session.add_all([class_one, class_two, class_three, subject_one, subject_two])
    db_session.flush()

    pair_one = ClassSubject(class_id=class_one.id, subject_id=subject_one.id)
    pair_two = ClassSubject(class_id=class_two.id, subject_id=subject_two.id)
    pair_three = ClassSubject(class_id=class_three.id, subject_id=subject_two.id)
    pair_four = ClassSubject(class_id=class_one.id, subject_id=subject_two.id)
    db_session.add_all([pair_one, pair_two, pair_three, pair_four])
    db_session.flush()

    teacher = make_user(
        email="timetable-teacher@example.com",
        password="StrongPass123",
        role_name="TEACHER",
    )
    teacher_staff = Staff(
        school_id=school.id, staff_number="TMT-T-001",
        first_name="Mpho", last_name="Teacher", user_id=teacher.id,
        employment_status="active", is_active=True,
    )
    other_staff = Staff(
        school_id=school.id, staff_number="TMT-T-002",
        first_name="Neo", last_name="Teacher",
        employment_status="active", is_active=True,
    )
    third_staff = Staff(
        school_id=school.id, staff_number="TMT-T-003",
        first_name="Tariro", last_name="Teacher",
        employment_status="active", is_active=True,
    )
    db_session.add_all([teacher_staff, other_staff, third_staff])
    db_session.flush()
    db_session.add_all([
        UserSchool(user_id=teacher.id, school_id=school.id),
        TeachingAssignment(
            school_id=school.id, staff_id=teacher_staff.id, class_subject_id=pair_one.id,
            start_date=academic_year.start_date, is_active=True, is_primary=True,
        ),
        TeachingAssignment(
            school_id=school.id, staff_id=other_staff.id, class_subject_id=pair_two.id,
            start_date=academic_year.start_date, is_active=True, is_primary=True,
        ),
        TeachingAssignment(
            school_id=school.id, staff_id=third_staff.id, class_subject_id=pair_three.id,
            start_date=academic_year.start_date, is_active=True, is_primary=True,
        ),
        TeachingAssignment(
            school_id=school.id, staff_id=third_staff.id, class_subject_id=pair_four.id,
            start_date=academic_year.start_date, is_active=True, is_primary=True,
        ),
    ])
    db_session.commit()

    make_user(email="timetable-admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    admin_headers = auth_headers("timetable-admin@example.com", "StrongPass123")
    teacher_headers = auth_headers("timetable-teacher@example.com", "StrongPass123")
    params = {"school_id": str(school.id)}

    first = client.post(
        "/api/v1/timetable",
        headers=admin_headers,
        params=params,
        json={
            "staff_id": str(teacher_staff.id),
            "class_subject_id": str(pair_one.id),
            "weekday": 0,
            "start_time": "08:00",
            "end_time": "08:40",
            "room": "Room 1",
            "effective_from": academic_year.start_date.isoformat(),
            "effective_to": academic_year.end_date.isoformat(),
        },
    )
    assert first.status_code == 201, first.text
    first_id = first.json()["id"]
    assert first.json()["academic_year_id"] == str(academic_year.id)

    second = client.post(
        "/api/v1/timetable",
        headers=admin_headers,
        params=params,
        json={
            "staff_id": str(other_staff.id),
            "class_subject_id": str(pair_two.id),
            "weekday": 0,
            "start_time": "09:00",
            "end_time": "09:40",
            "room": "Room 2",
            "effective_from": academic_year.start_date.isoformat(),
            "effective_to": academic_year.end_date.isoformat(),
        },
    )
    assert second.status_code == 201, second.text

    admin_list = client.get("/api/v1/timetable", headers=admin_headers, params=params)
    assert admin_list.status_code == 200, admin_list.text
    assert len(admin_list.json()) == 2

    teacher_list = client.get("/api/v1/timetable", headers=teacher_headers, params=params)
    assert teacher_list.status_code == 200, teacher_list.text
    assert len(teacher_list.json()) == 1
    assert teacher_list.json()[0]["id"] == first_id
    assert teacher_list.json()[0]["teacher_name"] == "Mpho Teacher"

    overlap = client.post(
        "/api/v1/timetable",
        headers=admin_headers,
        params=params,
        json={
            "staff_id": str(teacher_staff.id),
            "class_subject_id": str(pair_one.id),
            "weekday": 0,
            "start_time": "08:20",
            "end_time": "09:00",
            "effective_from": academic_year.start_date.isoformat(),
            "effective_to": academic_year.end_date.isoformat(),
        },
    )
    assert overlap.status_code == 409, overlap.text
    assert overlap.json()["error"]["code"] == "TIMETABLE_TEACHER_CONFLICT"

    class_clash = client.post(
        "/api/v1/timetable", headers=admin_headers, params=params,
        json={
            "staff_id": str(third_staff.id), "class_subject_id": str(pair_four.id),
            "weekday": 0, "start_time": "08:20", "end_time": "09:00",
            "effective_from": academic_year.start_date.isoformat(),
            "effective_to": academic_year.end_date.isoformat(),
        },
    )
    assert class_clash.status_code == 409
    assert class_clash.json()["error"]["code"] == "TIMETABLE_CLASS_CONFLICT"

    room_clash = client.post(
        "/api/v1/timetable", headers=admin_headers, params=params,
        json={
            "staff_id": str(third_staff.id), "class_subject_id": str(pair_three.id),
            "weekday": 0, "start_time": "08:20", "end_time": "09:00",
            "room": " room 1 ", "effective_from": academic_year.start_date.isoformat(),
            "effective_to": academic_year.end_date.isoformat(),
        },
    )
    assert room_clash.status_code == 409
    assert room_clash.json()["error"]["code"] == "TIMETABLE_ROOM_CONFLICT"

    published = client.post(
        f"/api/v1/timetable/publish/{academic_year.id}",
        headers=admin_headers, params=params,
    )
    assert published.status_code == 200, published.text
    assert published.json()["published"] is True
    locked_delete = client.delete(f"/api/v1/timetable/{first_id}", headers=admin_headers)
    assert locked_delete.status_code == 409, locked_delete.text
    assert locked_delete.json()["error"]["code"] == "TIMETABLE_PUBLISHED"

    reopened = client.post(
        f"/api/v1/timetable/reopen/{academic_year.id}",
        headers=admin_headers, params=params,
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["published"] is False

    denied_delete = client.delete(f"/api/v1/timetable/{first_id}", headers=teacher_headers)
    assert denied_delete.status_code == 403, denied_delete.text
