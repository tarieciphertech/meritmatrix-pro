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
