"""Guardian in-app notification delivery and ownership tests."""
from app.models.guardian import Guardian
from app.models.school import School
from app.models.student import Student
from app.models.student_guardian import StudentGuardian
from app.services.notification_service import notify_guardians


def test_linked_guardian_receives_and_can_read_notification(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school = School(name="Notifications School", code="NOT001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    guardian = Guardian(
        school_id=school.id, first_name="Lesego", last_name="Parent",
        phone="+26775555555", email="notify-parent@example.com", is_active=True,
    )
    student = Student(
        school_id=school.id, student_number="NOT-STU-1",
        first_name="Kea", last_name="Student", status="active", is_active=True,
    )
    db_session.add_all([guardian, student])
    db_session.flush()
    db_session.add(StudentGuardian(
        student_id=student.id, guardian_id=guardian.id,
        relationship_type="mother", receives_notifications=True,
    ))
    user = make_user(
        email="notify-parent@example.com", password="StrongPass123", role_name="GUARDIAN",
        first_name="Lesego", last_name="Parent",
    )
    user.guardian_id = guardian.id
    db_session.commit()

    created = notify_guardians(
        db_session, school_id=school.id, student_ids=[student.id],
        notification_type="assessment.results_published",
        title="Academic results published",
        message="The school has published results for your child.",
        data={"assessment_id": "assessment-123"},
    )
    db_session.commit()
    assert created == 1

    headers = auth_headers("notify-parent@example.com", "StrongPass123")
    response = client.get(f"/api/v1/notifications?school_id={school.id}", headers=headers)
    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["title"] == "Academic results published"
    assert rows[0]["data"]["assessment_id"] == "assessment-123"
    notification_id = rows[0]["id"]

    mark_read = client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers, json={})
    assert mark_read.status_code == 200, mark_read.text
    assert mark_read.json()["read_at"] is not None

    unread = client.get(
        f"/api/v1/notifications?school_id={school.id}&unread_only=true",
        headers=headers,
    )
    assert unread.status_code == 200, unread.text
    assert unread.json() == []


def test_staff_account_sharing_guardian_email_does_not_receive_family_notifications(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school = School(name="Notification Email Collision", code="NEC001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    guardian = Guardian(
        school_id=school.id, first_name="Shared", last_name="Email",
        phone="+26777777777", email="shared-contact@example.com", is_active=True,
    )
    student = Student(
        school_id=school.id, student_number="NEC-STU-1",
        first_name="Linked", last_name="Student", status="active", is_active=True,
    )
    db_session.add_all([guardian, student])
    db_session.flush()
    db_session.add(StudentGuardian(
        student_id=student.id, guardian_id=guardian.id,
        relationship_type="mother", receives_notifications=True,
    ))
    make_user(
        email="shared-contact@example.com", password="StrongPass123",
        role_name="TEACHER", first_name="Staff", last_name="Account",
    )
    db_session.commit()

    created = notify_guardians(
        db_session, school_id=school.id, student_ids=[student.id],
        notification_type="attendance.absent", title="Attendance absence recorded",
        message="An absence was recorded.",
    )
    db_session.commit()

    assert created == 0
    headers = auth_headers("shared-contact@example.com", "StrongPass123")
    response = client.get(f"/api/v1/notifications?school_id={school.id}", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == []


def test_user_cannot_mark_another_users_notification_as_read(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school = School(name="Notification Privacy School", code="NPS001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    guardian = Guardian(
        school_id=school.id, first_name="Privacy", last_name="Parent",
        phone="+26776666666", email="privacy-parent@example.com", is_active=True,
    )
    student = Student(
        school_id=school.id, student_number="NPS-STU-1",
        first_name="Private", last_name="Student", status="active", is_active=True,
    )
    db_session.add_all([guardian, student])
    db_session.flush()
    db_session.add(StudentGuardian(student_id=student.id, guardian_id=guardian.id, relationship_type="guardian"))
    guardian_user = make_user(
        email="privacy-parent@example.com", password="StrongPass123", role_name="GUARDIAN",
    )
    guardian_user.guardian_id = guardian.id
    other_user = make_user(
        email="other-notification-user@example.com", password="StrongPass123", role_name="GUARDIAN",
    )
    db_session.commit()
    notify_guardians(
        db_session, school_id=school.id, student_ids=[student.id],
        notification_type="fees.charge_created", title="New school fee charge",
        message="A new fee charge was added.",
    )
    db_session.commit()

    notification = client.get(
        f"/api/v1/notifications?school_id={school.id}",
        headers=auth_headers("privacy-parent@example.com", "StrongPass123"),
    ).json()[0]
    other_headers = auth_headers("other-notification-user@example.com", "StrongPass123")
    response = client.post(f"/api/v1/notifications/{notification['id']}/read", headers=other_headers, json={})

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"

def test_school_role_notifications_are_limited_to_matching_school_members(
    make_user, seeded_rbac, db_session
):
    from app.models.user_school import UserSchool
    from app.models.user_notification import UserNotification
    from app.services.notification_service import notify_school_roles

    school = School(name="Staff Notifications School", code="SNS001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    admin = make_user(
        email="staff-notification-admin@example.com", password="StrongPass123",
        role_name="SCHOOL_ADMIN",
    )
    teacher = make_user(
        email="staff-notification-teacher@example.com", password="StrongPass123",
        role_name="TEACHER",
    )
    unlinked_admin = make_user(
        email="staff-notification-unlinked@example.com", password="StrongPass123",
        role_name="SCHOOL_ADMIN",
    )
    db_session.add_all([
        UserSchool(user_id=admin.id, school_id=school.id),
        UserSchool(user_id=teacher.id, school_id=school.id),
    ])
    db_session.flush()

    count = notify_school_roles(
        db_session,
        school_id=school.id,
        role_names={"SCHOOL_ADMIN"},
        notification_type="assessment.marks_submitted_for_review",
        title="Marks ready for review",
        message="An assessment is ready for review.",
        data={"assessment_id": "assessment-1"},
        exclude_user_id=teacher.id,
    )
    db_session.commit()

    rows = db_session.query(UserNotification).filter(
        UserNotification.school_id == school.id
    ).all()
    assert count == 1
    assert len(rows) == 1
    assert rows[0].recipient_user_id == admin.id
    assert rows[0].recipient_user_id != unlinked_admin.id

