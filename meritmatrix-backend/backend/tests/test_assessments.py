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
    staff = SimpleNamespace(id=uuid4(), user_id=uuid4(), school_id=school_id, is_active=True, employment_status="active")

    class Query:
        def __init__(self, first=None, rows=None):
            self.first_value = first
            self.rows = rows or []

        def filter(self, *args, **kwargs):
            return self

        def join(self, *args, **kwargs):
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



def test_marks_must_be_submitted_for_review_before_publication(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    """A draft cannot be published; complete marks must be submitted before admin publication."""
    from datetime import date

    from app.models.academic_year import AcademicYear
    from app.models.class_subject import ClassSubject
    from app.models.clazz import Class
    from app.models.enrollment import Enrollment, EnrollmentStatus
    from app.models.school import School
    from app.models.student import Student
    from app.models.subject import Subject
    from app.models.term import Term

    school = School(name="Review School", code="REV001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    year = AcademicYear(
        school_id=school.id, name="2026", start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31), is_current=True, is_active=True,
    )
    clazz = Class(school_id=school.id, name="Form 1", code="F1", level=1, is_active=True)
    subject = Subject(school_id=school.id, name="Mathematics", code="MATH", is_active=True)
    db_session.add_all([year, clazz, subject])
    db_session.flush()
    term = Term(
        academic_year_id=year.id, name="Term 3", term_number=3,
        start_date=date(2026, 9, 1), end_date=date(2026, 12, 31),
        is_current=True, is_active=True,
    )
    class_subject = ClassSubject(class_id=clazz.id, subject_id=subject.id)
    student = Student(
        school_id=school.id, student_number="REV-STU-1",
        first_name="Ada", last_name="Molefe", status="active", is_active=True,
    )
    db_session.add_all([term, class_subject, student])
    db_session.flush()
    enrollment = Enrollment(
        student_id=student.id, academic_year_id=year.id, class_id=clazz.id,
        enrollment_date=date(2026, 1, 12), status=EnrollmentStatus.ACTIVE,
    )
    db_session.add(enrollment)
    db_session.commit()

    make_user(email="review-admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("review-admin@example.com", "StrongPass123")

    subjects = client.get(
        f"/api/v1/class-subjects?class_id={clazz.id}",
        headers=headers,
    )
    assert subjects.status_code == 200, subjects.text
    assert subjects.json()[0]["subject_name"] == "Mathematics"
    assert subjects.json()[0]["subject_code"] == "MATH"

    created = client.post(
        f"/api/v1/assessments?school_id={school.id}",
        headers=headers,
        json={
            "class_subject_id": str(class_subject.id),
            "term_id": str(term.id),
            "title": "Term 3 Mathematics Test",
            "assessment_type": "test",
            "assessment_date": "2026-10-17",
            "max_score": 100,
            "weight_percent": 100,
            # Even a client attempting to publish during creation must be ignored.
            "is_published": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["is_published"] is False
    assert created.json()["marks_submitted"] is False
    assessment_id = created.json()["id"]

    premature_publish = client.patch(
        f"/api/v1/assessments/{assessment_id}",
        headers=headers,
        json={"is_published": True},
    )
    assert premature_publish.status_code == 409, premature_publish.text
    assert premature_publish.json()["error"]["code"] == "MARKS_NOT_SUBMITTED_FOR_REVIEW"

    saved = client.put(
        f"/api/v1/assessments/{assessment_id}/marks",
        headers=headers,
        json={"marks": [{"enrollment_id": str(enrollment.id), "score": 90}]},
    )
    assert saved.status_code == 200, saved.text

    submitted = client.post(
        f"/api/v1/assessments/{assessment_id}/submit-for-review",
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["marks_submitted"] is True
    assert submitted.json()["is_published"] is False

    from app.models.user_school import UserSchool

    teacher = make_user(email="review-teacher@example.com", password="StrongPass123", role_name="TEACHER")
    db_session.add(UserSchool(user_id=teacher.id, school_id=school.id))
    db_session.commit()
    teacher_headers = auth_headers("review-teacher@example.com", "StrongPass123")

    teacher_publish = client.patch(
        f"/api/v1/assessments/{assessment_id}",
        headers=teacher_headers,
        json={"is_published": True},
    )
    assert teacher_publish.status_code == 403, teacher_publish.text
    assert teacher_publish.json()["error"]["code"] == "ACADEMIC_ADMIN_REQUIRED"

    teacher_grade_edit = client.put(
        f"/api/v1/grading-scales?school_id={school.id}",
        headers=teacher_headers,
        json={"bands": [
            {"grade_label": "A", "min_percentage": 0, "max_percentage": 100},
        ]},
    )
    assert teacher_grade_edit.status_code == 403, teacher_grade_edit.text
    assert teacher_grade_edit.json()["error"]["code"] == "ACADEMIC_ADMIN_REQUIRED"

    published = client.patch(
        f"/api/v1/assessments/{assessment_id}",
        headers=headers,
        json={"is_published": True},
    )
    assert published.status_code == 200, published.text
    assert published.json()["is_published"] is True

    results = client.get(
        f"/api/v1/results?school_id={school.id}&class_id={clazz.id}&term_id={term.id}",
        headers=headers,
    )
    assert results.status_code == 200, results.text
    assert len(results.json()) == 1
    assert results.json()[0]["weighted_percentage"] == 90.0


def test_inactive_grading_bands_do_not_block_active_scale(client, make_user, auth_headers, seeded_rbac, db_session):
    from app.models.school import School

    school = School(name="Inactive Bands School", code="GRD001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.commit()
    make_user(email="inactive-bands-admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("inactive-bands-admin@example.com", "StrongPass123")

    response = client.put(
        f"/api/v1/grading-scales?school_id={school.id}",
        headers=headers,
        json={"bands": [
            {"grade_label": "A", "min_percentage": 80, "max_percentage": 100, "is_active": True},
            {"grade_label": "Old A", "min_percentage": 85, "max_percentage": 95, "is_active": False},
            {"grade_label": "B", "min_percentage": 0, "max_percentage": 79, "is_active": True},
        ]},
    )
    assert response.status_code == 200, response.text
    assert len(response.json()) == 3


def test_only_school_administrators_can_manage_school_grading(seeded_rbac, make_user, db_session):
    from app.routers.assessments import _is_school_administrator

    school_id = uuid4()
    teacher = make_user(email="grading-teacher@example.com", role_name="TEACHER")
    school_admin = make_user(email="grading-school-admin@example.com", role_name="SCHOOL_ADMIN")

    assert _is_school_administrator(db_session, teacher, school_id) is False
    assert _is_school_administrator(db_session, school_admin, school_id) is True
