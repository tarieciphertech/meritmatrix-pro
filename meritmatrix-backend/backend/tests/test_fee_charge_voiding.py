"""Fee charge correction tests for safe, auditable voiding."""
from datetime import date

from app.models.academic_year import AcademicYear
from app.models.school import School
from app.models.student import Student


def _setup_fee_charge(client, make_user, auth_headers, seeded_rbac, db_session, suffix):
    school = School(
        name=f"Void Fee School {suffix}", code=f"VFE{suffix}",
        city="Gaborone", country="Botswana",
    )
    db_session.add(school)
    db_session.flush()
    year = AcademicYear(
        school_id=school.id, name="2026",
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        is_current=True, is_active=True,
    )
    student = Student(
        school_id=school.id, student_number=f"VFE-STU-{suffix}",
        first_name="Kea", last_name="Learner", status="active", is_active=True,
    )
    db_session.add_all([year, student])
    db_session.commit()
    make_user(
        email=f"void-fees-admin-{suffix}@example.com",
        password="StrongPass123",
        role_name="SUPER_ADMIN",
    )
    headers = auth_headers(f"void-fees-admin-{suffix}@example.com", "StrongPass123")
    response = client.post(
        f"/api/v1/fees/charges?school_id={school.id}",
        headers=headers,
        json={
            "student_id": str(student.id),
            "academic_year_id": str(year.id),
            "description": "Incorrectly entered tuition charge",
            "amount": "150.00",
        },
    )
    assert response.status_code == 201, response.text
    return school, response.json(), headers


def test_unpaid_fee_charge_can_be_voided_and_remains_in_audit_history(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school, charge, headers = _setup_fee_charge(
        client, make_user, auth_headers, seeded_rbac, db_session, "001"
    )

    voided = client.post(
        f"/api/v1/fees/charges/{charge['id']}/void?school_id={school.id}",
        headers=headers,
        json={},
    )
    assert voided.status_code == 200, voided.text
    assert voided.json()["is_void"] is True

    from app.models.audit_log import AuditLog
    audit = db_session.query(AuditLog).filter(
        AuditLog.school_id == school.id,
        AuditLog.action == "fees.charge_voided",
        AuditLog.entity_id == charge["id"],
    ).one()
    assert audit.entity_type == "fee_charge"

    active_rows = client.get(
        f"/api/v1/fees/charges?school_id={school.id}",
        headers=headers,
    )
    assert active_rows.status_code == 200
    assert active_rows.json() == []

    all_rows = client.get(
        f"/api/v1/fees/charges?school_id={school.id}&include_void=true",
        headers=headers,
    )
    assert all_rows.status_code == 200
    assert len(all_rows.json()) == 1
    assert all_rows.json()[0]["is_void"] is True

    repeated = client.post(
        f"/api/v1/fees/charges/{charge['id']}/void?school_id={school.id}",
        headers=headers,
        json={},
    )
    assert repeated.status_code == 200
    assert repeated.json()["is_void"] is True


def test_fee_charge_with_a_recorded_payment_cannot_be_voided(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school, charge, headers = _setup_fee_charge(
        client, make_user, auth_headers, seeded_rbac, db_session, "002"
    )
    payment = client.post(
        f"/api/v1/fees/payments?school_id={school.id}",
        headers=headers,
        json={
            "charge_id": charge["id"],
            "payment_date": "2026-11-26",
            "amount": 25.0,
            "method": "cash",
            "reference": "VFE-PAID-002",
        },
    )
    assert payment.status_code == 201, payment.text

    response = client.post(
        f"/api/v1/fees/charges/{charge['id']}/void?school_id={school.id}",
        headers=headers,
        json={},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FEE_CHARGE_HAS_PAYMENTS"

    still_active = client.get(
        f"/api/v1/fees/charges?school_id={school.id}",
        headers=headers,
    )
    assert still_active.status_code == 200
    assert still_active.json()[0]["is_void"] is False
