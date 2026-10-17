"""Guardian portal school isolation and linked-student authorization tests."""
from app.models.guardian import Guardian
from app.models.school import School
from app.models.student import Student
from app.models.student_guardian import StudentGuardian


def test_guardian_portal_only_lists_linked_school_and_students(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school_a = School(name="Guardian School A", code="GPA001", city="Gaborone", country="Botswana")
    school_b = School(name="Guardian School B", code="GPB001", city="Gaborone", country="Botswana")
    db_session.add_all([school_a, school_b])
    db_session.flush()

    guardian_a = Guardian(
        school_id=school_a.id, first_name="Mpho", last_name="Guardian",
        phone="+26771111111", email="guardian-a@example.com", is_active=True,
    )
    guardian_b = Guardian(
        school_id=school_b.id, first_name="Kabelo", last_name="Guardian",
        phone="+26772222222", email="guardian-b@example.com", is_active=True,
    )
    student_a = Student(
        school_id=school_a.id, student_number="GPA-STU-1",
        first_name="Neo", last_name="A", status="active", is_active=True,
    )
    student_b = Student(
        school_id=school_b.id, student_number="GPB-STU-1",
        first_name="Neo", last_name="B", status="active", is_active=True,
    )
    db_session.add_all([guardian_a, guardian_b, student_a, student_b])
    db_session.flush()
    db_session.add_all([
        StudentGuardian(student_id=student_a.id, guardian_id=guardian_a.id, relationship_type="mother"),
        StudentGuardian(student_id=student_b.id, guardian_id=guardian_b.id, relationship_type="mother"),
    ])
    user = make_user(
        email="guardian-a@example.com", password="StrongPass123", role_name="GUARDIAN",
        first_name="Mpho", last_name="Guardian",
    )
    user.guardian_id = guardian_a.id
    db_session.commit()

    headers = auth_headers("guardian-a@example.com", "StrongPass123")
    schools_response = client.get("/api/v1/guardian-portal/schools", headers=headers)
    assert schools_response.status_code == 200, schools_response.text
    schools = schools_response.json()
    assert [row["id"] for row in schools] == [str(school_a.id)]

    students_response = client.get("/api/v1/guardian-portal/students", headers=headers)
    assert students_response.status_code == 200, students_response.text
    students = students_response.json()
    assert [row["student_number"] for row in students] == ["GPA-STU-1"]

    forbidden = client.get(
        f"/api/v1/guardian-portal/students?school_id={school_b.id}",
        headers=headers,
    )
    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["error"]["code"] == "GUARDIAN_SCHOOL_ACCESS_DENIED"


def test_guardian_portal_does_not_discover_students_from_an_unbound_account(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school = School(name="Unbound Guardian School", code="UGS001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    guardian = Guardian(
        school_id=school.id, first_name="Unbound", last_name="Guardian",
        phone="+26773333333", email="different-address@example.com", is_active=True,
    )
    student = Student(
        school_id=school.id, student_number="UGS-STU-1",
        first_name="Private", last_name="Student", status="active", is_active=True,
    )
    db_session.add_all([guardian, student])
    db_session.flush()
    db_session.add(StudentGuardian(student_id=student.id, guardian_id=guardian.id, relationship_type="guardian"))
    make_user(
        email="unbound-user@example.com", password="StrongPass123", role_name="GUARDIAN",
        first_name="Unbound", last_name="User",
    )
    db_session.commit()

    headers = auth_headers("unbound-user@example.com", "StrongPass123")
    schools_response = client.get("/api/v1/guardian-portal/schools", headers=headers)
    students_response = client.get("/api/v1/guardian-portal/students", headers=headers)

    assert schools_response.status_code == 200, schools_response.text
    assert schools_response.json() == []
    assert students_response.status_code == 200, students_response.text
    assert students_response.json() == []



def test_guardian_portal_shows_only_published_results_attendance_and_fee_balance(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    from datetime import date
    from decimal import Decimal

    from app.models.academic_year import AcademicYear
    from app.models.assessment import Assessment, AssessmentMark
    from app.models.attendance_record import AttendanceRecord
    from app.models.class_subject import ClassSubject
    from app.models.clazz import Class
    from app.models.enrollment import Enrollment, EnrollmentStatus
    from app.models.fee import FeeCharge, FeePayment
    from app.models.grading_band import GradingBand
    from app.models.subject import Subject
    from app.models.term import Term

    school = School(
        name="Progress Portal School", code="PPS001", city="Gaborone",
        country="Botswana", currency="BWP", is_active=True,
    )
    db_session.add(school)
    db_session.flush()
    guardian = Guardian(
        school_id=school.id, first_name="Boitumelo", last_name="Parent",
        phone="+26774444444", email="progress-parent@example.com", is_active=True,
    )
    student = Student(
        school_id=school.id, student_number="PPS-STU-1",
        first_name="Naledi", last_name="Student", status="active", is_active=True,
    )
    year = AcademicYear(
        school_id=school.id, name="2026", start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31), is_current=True, is_active=True,
    )
    clazz = Class(school_id=school.id, name="Form 1", code="F1", level=1, is_active=True)
    subject = Subject(school_id=school.id, name="Mathematics", code="MATH", is_active=True)
    db_session.add_all([guardian, student, year, clazz, subject])
    db_session.flush()
    relationship = StudentGuardian(
        student_id=student.id, guardian_id=guardian.id,
        relationship_type="mother", is_primary=True, receives_notifications=True,
    )
    term = Term(
        academic_year_id=year.id, name="Term 3", term_number=3,
        start_date=date(2026, 9, 1), end_date=date(2026, 12, 31),
        is_current=True, is_active=True,
    )
    class_subject = ClassSubject(class_id=clazz.id, subject_id=subject.id)
    db_session.add_all([relationship, term, class_subject])
    db_session.flush()
    enrollment = Enrollment(
        student_id=student.id, academic_year_id=year.id, class_id=clazz.id,
        enrollment_date=date(2026, 1, 12), status=EnrollmentStatus.ACTIVE,
    )
    db_session.add(enrollment)
    db_session.flush()
    assessment = Assessment(
        school_id=school.id, class_subject_id=class_subject.id, term_id=term.id,
        title="Mathematics Test", assessment_type="test", assessment_date=date(2026, 10, 1),
        max_score=100, weight_percent=100, is_published=True, marks_submitted=True,
    )
    band = GradingBand(
        school_id=school.id, grade_label="A", min_percentage=80,
        max_percentage=100, comment="Excellent", display_order=1, is_active=True,
    )
    charge = FeeCharge(
        school_id=school.id, student_id=student.id, academic_year_id=year.id,
        term_id=term.id, description="Term 3 tuition", amount=Decimal("1000.00"),
        due_date=date(2026, 10, 1), is_void=False,
    )
    db_session.add_all([assessment, band, charge])
    db_session.flush()
    db_session.add_all([
        AssessmentMark(
            assessment_id=assessment.id, enrollment_id=enrollment.id,
            score=90, remarks="Very good",
        ),
        AttendanceRecord(
            school_id=school.id, enrollment_id=enrollment.id,
            attendance_date=date(2026, 10, 2), session="full_day", status="present",
        ),
        FeePayment(
            school_id=school.id, student_id=student.id, charge_id=charge.id,
            payment_date=date(2026, 10, 3), amount=Decimal("400.00"),
            method="cash", reference="PPS-PAY-1",
        ),
    ])
    user = make_user(
        email="progress-parent@example.com", password="StrongPass123",
        role_name="GUARDIAN", first_name="Boitumelo", last_name="Parent",
    )
    user.guardian_id = guardian.id
    db_session.commit()

    headers = auth_headers("progress-parent@example.com", "StrongPass123")
    response = client.get(
        f"/api/v1/guardian-portal/students?school_id={school.id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) == 1
    record = data[0]
    assert record["student_number"] == "PPS-STU-1"
    assert record["subjects"][0]["name"] == "Mathematics"
    assert record["academic_results"][0]["assessment_title"] == "Mathematics Test"
    assert record["academic_results"][0]["grade_label"] == "A"
    assert record["attendance"]["present"] == 1
    assert record["attendance"]["attendance_rate"] == 100.0
    assert record["fee_summary"]["currency"] == "BWP"
    assert record["fee_summary"]["charges_total"] == 1000.0
    assert record["fee_summary"]["payments_total"] == 400.0
    assert record["fee_summary"]["balance"] == 600.0


def test_non_guardian_account_cannot_use_legacy_email_matching(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    """Email equality alone must not turn a staff account into a guardian portal session."""
    school = School(name="Email Collision School", code="ECS001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    guardian = Guardian(
        school_id=school.id, first_name="Parent", last_name="Record",
        phone="+26775555555", email="staff-parent@example.com", is_active=True,
    )
    student = Student(
        school_id=school.id, student_number="ECS-STU-1",
        first_name="Private", last_name="Student", status="active", is_active=True,
    )
    db_session.add_all([guardian, student])
    db_session.flush()
    db_session.add(StudentGuardian(
        student_id=student.id, guardian_id=guardian.id, relationship_type="mother",
    ))
    make_user(
        email="staff-parent@example.com", password="StrongPass123",
        role_name="TEACHER", first_name="Staff", last_name="Account",
    )
    db_session.commit()

    headers = auth_headers("staff-parent@example.com", "StrongPass123")
    schools_response = client.get("/api/v1/guardian-portal/schools", headers=headers)
    students_response = client.get("/api/v1/guardian-portal/students", headers=headers)

    assert schools_response.status_code == 403, schools_response.text
    assert schools_response.json()["error"]["code"] == "ROLE_DENIED"
    assert students_response.status_code == 403, students_response.text
    assert students_response.json()["error"]["code"] == "ROLE_DENIED"


def test_legacy_parent_role_keeps_email_linked_portal_access(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    """Legacy PARENT users remain in the guardian portal while accounts are migrated."""
    school = School(name="Legacy Parent School", code="LPS001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    guardian = Guardian(
        school_id=school.id, first_name="Legacy", last_name="Parent",
        phone="+26776666666", email="legacy-parent@example.com", is_active=True,
    )
    student = Student(
        school_id=school.id, student_number="LPS-STU-1",
        first_name="Linked", last_name="Student", status="active", is_active=True,
    )
    db_session.add_all([guardian, student])
    db_session.flush()
    db_session.add(StudentGuardian(
        student_id=student.id, guardian_id=guardian.id, relationship_type="parent",
    ))
    make_user(
        email="legacy-parent@example.com", password="StrongPass123",
        role_name="PARENT", first_name="Legacy", last_name="Parent",
    )
    db_session.commit()

    headers = auth_headers("legacy-parent@example.com", "StrongPass123")
    response = client.get("/api/v1/guardian-portal/students", headers=headers)

    assert response.status_code == 200, response.text
    assert [row["student_number"] for row in response.json()] == ["LPS-STU-1"]
