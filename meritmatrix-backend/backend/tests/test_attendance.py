"""Daily attendance register CRUD, validation and history-linked roster tests."""
from datetime import date

from app.models.academic_year import AcademicYear
from app.models.clazz import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.school import School
from app.models.student import Student


def _setup_register(db_session):
    school = School(name="Attendance School", code="ATT001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    year = AcademicYear(school_id=school.id, name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
    clazz = Class(school_id=school.id, name="Standard 5", code="STD5", level=5)
    student_a = Student(school_id=school.id, student_number="A001", first_name="Ada", last_name="Molefe", status="active")
    student_b = Student(school_id=school.id, student_number="A002", first_name="Kabelo", last_name="Moyo", status="active")
    db_session.add_all([year, clazz, student_a, student_b])
    db_session.flush()
    enrollments = [
        Enrollment(student_id=student.id, academic_year_id=year.id, class_id=clazz.id, enrollment_date=date(2026, 1, 12), status=EnrollmentStatus.ACTIVE)
        for student in (student_a, student_b)
    ]
    db_session.add_all(enrollments)
    db_session.commit()
    return school, year, clazz, enrollments


def test_attendance_roster_and_register_save(client, make_user, auth_headers, seeded_rbac, db_session):
    school, year, clazz, enrollments = _setup_register(db_session)
    make_user(email="attendance-admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("attendance-admin@example.com", "StrongPass123")
    params = {"school_id": str(school.id), "class_id": str(clazz.id), "attendance_date": "2026-03-02"}

    roster = client.get("/api/v1/attendance/roster", headers=headers, params=params)
    assert roster.status_code == 200, roster.text
    assert len(roster.json()) == 2
    assert {row["status"] for row in roster.json()} == {"unmarked"}

    payload = {
        "attendance_date": "2026-03-02",
        "session": "full_day",
        "entries": [
            {"enrollment_id": str(enrollments[0].id), "status": "present"},
            {"enrollment_id": str(enrollments[1].id), "status": "absent", "notes": "No notice received"},
        ],
    }
    saved = client.put("/api/v1/attendance/register", headers=headers, params={"school_id": str(school.id), "class_id": str(clazz.id)}, json=payload)
    assert saved.status_code == 200, saved.text
    assert len(saved.json()) == 2
    assert {row["status"] for row in saved.json()} == {"present", "absent"}

    payload["entries"][0]["status"] = "late"
    resaved = client.put("/api/v1/attendance/register", headers=headers, params={"school_id": str(school.id), "class_id": str(clazz.id)}, json=payload)
    assert resaved.status_code == 200, resaved.text
    assert len(resaved.json()) == 2
    assert sum(row["status"] == "late" for row in resaved.json()) == 1

    listed = client.get("/api/v1/attendance", headers=headers, params={**params, "session": "full_day"})
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 2


def test_attendance_rejects_duplicate_enrollment_in_same_payload(client, make_user, auth_headers, seeded_rbac, db_session):
    school, year, clazz, enrollments = _setup_register(db_session)
    make_user(email="attendance-dup@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("attendance-dup@example.com", "StrongPass123")
    payload = {
        "attendance_date": "2026-03-02",
        "session": "full_day",
        "entries": [
            {"enrollment_id": str(enrollments[0].id), "status": "present"},
            {"enrollment_id": str(enrollments[0].id), "status": "absent"},
        ],
    }
    response = client.put(
        "/api/v1/attendance/register",
        headers=headers,
        params={"school_id": str(school.id), "class_id": str(clazz.id)},
        json=payload,
    )
    assert response.status_code == 422, response.text


def test_attendance_rejects_date_outside_academic_year(client, make_user, auth_headers, seeded_rbac, db_session):
    school, year, clazz, enrollments = _setup_register(db_session)
    make_user(email="attendance-date@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("attendance-date@example.com", "StrongPass123")
    response = client.get(
        "/api/v1/attendance/roster",
        headers=headers,
        params={"school_id": str(school.id), "class_id": str(clazz.id), "attendance_date": "2027-01-05"},
    )
    assert response.status_code == 409, response.text

def test_linked_teacher_can_only_open_attendance_for_assigned_class(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    """A staff-linked teacher can open assigned registers but not other classes."""
    from app.models.class_subject import ClassSubject
    from app.models.staff import Staff
    from app.models.subject import Subject
    from app.models.teaching_assignment import TeachingAssignment
    from app.models.user_school import UserSchool

    school, year, assigned_class, enrollments = _setup_register(db_session)
    other_class = Class(school_id=school.id, name="Standard 6", code="STD6", level=6)
    subject = Subject(school_id=school.id, name="Mathematics", code="MATH")
    db_session.add_all([other_class, subject])
    db_session.flush()
    pair = ClassSubject(class_id=assigned_class.id, subject_id=subject.id)
    db_session.add(pair)
    teacher = make_user(
        email="assigned-attendance-teacher@example.com",
        password="StrongPass123",
        role_name="TEACHER",
    )
    db_session.add(UserSchool(user_id=teacher.id, school_id=school.id))
    staff = Staff(
        school_id=school.id,
        staff_number="T-001",
        first_name="Tariro",
        last_name="Teacher",
        employment_status="active",
        is_active=True,
        user_id=teacher.id,
    )
    db_session.add(staff)
    db_session.flush()
    db_session.add(TeachingAssignment(
        school_id=school.id,
        staff_id=staff.id,
        class_subject_id=pair.id,
        start_date=date(2026, 1, 1),
        is_active=True,
    ))
    db_session.commit()
    headers = auth_headers("assigned-attendance-teacher@example.com", "StrongPass123")
    params = {"school_id": str(school.id), "attendance_date": "2026-03-02"}

    classes = client.get(
        "/api/v1/classes",
        headers=headers,
        params={"school_id": str(school.id), "on_date": "2026-03-02"},
    )
    assert classes.status_code == 200, classes.text
    assert [row["id"] for row in classes.json()] == [str(assigned_class.id)]

    allowed = client.get(
        "/api/v1/attendance/roster",
        headers=headers,
        params={**params, "class_id": str(assigned_class.id)},
    )
    assert allowed.status_code == 200, allowed.text
    assert len(allowed.json()) == 2

    denied = client.get(
        "/api/v1/attendance/roster",
        headers=headers,
        params={**params, "class_id": str(other_class.id)},
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["error"]["code"] == "TEACHING_ASSIGNMENT_REQUIRED"

    denied_class_detail = client.get(
        f"/api/v1/classes/{other_class.id}",
        headers=headers,
    )
    assert denied_class_detail.status_code == 403, denied_class_detail.text
    assert denied_class_detail.json()["error"]["code"] == "TEACHING_ASSIGNMENT_REQUIRED"
