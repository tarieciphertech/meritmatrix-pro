"""School audit history authorization and isolation tests."""
from datetime import datetime, timezone

from app.models.audit_log import AuditLog
from app.models.school import School


def test_audit_history_is_filtered_to_requested_school(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school_a = School(name="Audit School A", code="AUD001", city="Gaborone", country="Botswana")
    school_b = School(name="Audit School B", code="AUD002", city="Gaborone", country="Botswana")
    db_session.add_all([school_a, school_b])
    db_session.flush()
    db_session.add_all([
        AuditLog(
            school_id=school_a.id, actor_user_id=None, action="attendance.register_saved",
            entity_type="attendance_register", entity_id="class-a",
            details={"entries_count": 12},
        ),
        AuditLog(
            school_id=school_b.id, actor_user_id=None, action="fees.payment_recorded",
            entity_type="fee_payment", entity_id="payment-b",
            details={"amount": "25.00"},
        ),
    ])
    db_session.commit()

    make_user(email="audit-super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("audit-super@example.com", "StrongPass123")
    response = client.get(f"/api/v1/audit-logs?school_id={school_a.id}", headers=headers)

    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["school_id"] == str(school_a.id)
    assert rows[0]["action"] == "attendance.register_saved"
    assert rows[0]["details"]["entries_count"] == 12


def test_teachers_cannot_read_audit_history(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school = School(name="Restricted Audit School", code="AUD003", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.commit()
    make_user(email="audit-teacher@example.com", password="StrongPass123", role_name="TEACHER")
    headers = auth_headers("audit-teacher@example.com", "StrongPass123")

    response = client.get(f"/api/v1/audit-logs?school_id={school.id}", headers=headers)

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
