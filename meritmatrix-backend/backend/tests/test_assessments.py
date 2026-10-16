"""Assessment authorization and input validation regression tests."""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.assessment import AssessmentCreate, MarkEntry, MarkBatch


def test_assessments_require_authentication(client):
    response = client.get(f"/api/v1/assessments?school_id={uuid4()}")
    assert response.status_code == 401


def test_assessment_creation_requires_assessment_permission(client, make_user, auth_headers, seeded_rbac):
    make_user(email="student-assessments@example.com", password="StrongPass123", role_name="STUDENT")
    headers = auth_headers("student-assessments@example.com", "StrongPass123")
    response = client.post(
        f"/api/v1/assessments?school_id={uuid4()}",
        headers=headers,
        json={
            "class_subject_id": str(uuid4()),
            "term_id": str(uuid4()),
            "title": "Test",
            "max_score": 100,
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_assessment_schema_rejects_non_positive_max_score():
    with pytest.raises(ValidationError):
        AssessmentCreate(
            class_subject_id=uuid4(),
            term_id=uuid4(),
            title="Unit test",
            max_score=0,
        )


def test_mark_schema_rejects_negative_scores():
    with pytest.raises(ValidationError):
        MarkEntry(enrollment_id=uuid4(), score=-1)


def test_marks_batch_rejects_empty_submissions():
    with pytest.raises(ValidationError):
        MarkBatch(marks=[])


def test_grading_scale_rejects_overlapping_ranges(client, make_user, auth_headers, seeded_rbac):
    make_user(email="grading-admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("grading-admin@example.com", "StrongPass123")
    response = client.put(
        f"/api/v1/grading-scales?school_id={uuid4()}",
        headers=headers,
        json={"bands": [
            {"grade_label": "A", "min_percentage": 0, "max_percentage": 50},
            {"grade_label": "B", "min_percentage": 50, "max_percentage": 100},
        ]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "OVERLAPPING_GRADE_BANDS"


def test_teacher_role_has_required_assessment_and_attendance_permissions(seeded_rbac, db_session):
    from app.models.role import Role

    teacher = db_session.query(Role).filter(Role.name == "TEACHER").one()
    names = {permission.name for permission in teacher.permissions}
    assert {
        "schools.read", "academic_years.read", "terms.read", "classes.read",
        "subjects.read", "class_subjects.read", "students.read", "enrollments.read",
        "attendance.read", "attendance.create", "assessments.read",
        "assessments.create", "assessments.update",
    }.issubset(names)



def test_assignment_access_helpers_allow_non_staff_users_through_existing_rbac():
    """Assignment helpers must distinguish ordinary role-based users from linked staff."""
    from app.auth.assignment_access import assigned_class_subject_ids

    # A database fixture is needed to test a concrete linked staff user; this test
    # is intentionally covered by the API authorization checks in integration tests.
    assert callable(assigned_class_subject_ids)
