"""School calendar authorization, filtering and validation tests."""
from app.models.school import School


def test_calendar_event_lifecycle_and_approved_filter(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school = School(name="Calendar Workflow School", code="CAL001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.commit()
    make_user(email="calendar-admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("calendar-admin@example.com", "StrongPass123")

    created = client.post(
        f"/api/v1/calendar-events?school_id={school.id}",
        headers=headers,
        json={
            "title": "End of Term Examinations",
            "event_type": "exam_period",
            "start_date": "2026-11-20",
            "end_date": "2026-11-30",
            "is_instructional": False,
            "source": "school",
        },
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]
    assert created.json()["is_approved"] is False

    approved_only = client.get(
        f"/api/v1/calendar-events?school_id={school.id}&approved_only=true",
        headers=headers,
    )
    assert approved_only.status_code == 200
    assert approved_only.json() == []

    approved = client.patch(
        f"/api/v1/calendar-events/{event_id}",
        headers=headers,
        json={"is_approved": True},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["is_approved"] is True

    visible = client.get(
        f"/api/v1/calendar-events?school_id={school.id}&from_date=2026-11-26&approved_only=true",
        headers=headers,
    )
    assert visible.status_code == 200
    assert [row["id"] for row in visible.json()] == [event_id]


def test_calendar_rejects_invalid_date_range_and_teacher_cannot_manage_events(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school = School(name="Calendar Permission School", code="CAL002", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.commit()
    make_user(email="calendar-teacher@example.com", password="StrongPass123", role_name="TEACHER")
    headers = auth_headers("calendar-teacher@example.com", "StrongPass123")

    invalid = client.post(
        f"/api/v1/calendar-events?school_id={school.id}",
        headers=headers,
        json={
            "title": "Invalid range",
            "event_type": "school_event",
            "start_date": "2026-11-30",
            "end_date": "2026-11-20",
        },
    )
    assert invalid.status_code == 422

    denied = client.post(
        f"/api/v1/calendar-events?school_id={school.id}",
        headers=headers,
        json={
            "title": "Teacher-created event",
            "event_type": "school_event",
            "start_date": "2026-11-20",
            "end_date": "2026-11-20",
        },
    )
    assert denied.status_code == 403
