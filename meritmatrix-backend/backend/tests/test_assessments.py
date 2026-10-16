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



def test_assignment_access_helper_leaves_non_staff_accounts_on_existing_rbac():
    from types import SimpleNamespace
    from app.auth.assignment_access import assigned_class_subject_ids
    from app.models.staff import Staff

    class Query:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class DB:
        def query(self, model):
            assert model is Staff
            return Query()

    assert assigned_class_subject_ids(DB(), SimpleNamespace(id=uuid4()), uuid4()) is None


def test_assignment_access_denies_unassigned_class_subject():
    from datetime import date
    from types import SimpleNamespace

    from app.auth.assignment_access import require_class_subject_assignment
    from app.models.staff import Staff
    from app.models.teaching_assignment import TeachingAssignment
    from app.utils.errors import ForbiddenError

    school_id, assigned_subject_id, requested_subject_id = uuid4(), uuid4(), uuid4()
    staff = SimpleNamespace(id=uuid4(), user_id=uuid4(), school_id=school_id, is_active=True)

    class Query:
        def __init__(self, first=None, rows=None):
            self.first_value = first
            self.rows = rows or []

        def filter(self, *args, **kwargs):
            return self

        def distinct(self):
            return self

        def first(self):
            return self.first_value

        def all(self):
            return self.rows

    class DB:
        def query(self, model):
            if model is Staff:
                return Query(first=staff)
            assert model is TeachingAssignment.class_subject_id
            return Query(rows=[(assigned_subject_id,)])

    with pytest.raises(ForbiddenError) as exc:
        require_class_subject_assignment(
            DB(),
            SimpleNamespace(id=staff.user_id),
            school_id,
            requested_subject_id,
            date.today(),
        )
    assert exc.value.code == "CLASS_SUBJECT_ASSIGNMENT_REQUIRED"
