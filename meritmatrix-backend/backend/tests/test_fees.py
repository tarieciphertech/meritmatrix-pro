"""School-scoped fee charge and payment workflow tests."""
from datetime import date

from app.models.academic_year import AcademicYear
from app.models.school import School
from app.models.student import Student


def _fee_setup(db_session):
    school = School(name="Fee Workflow School", code="FEE001", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    year = AcademicYear(
        school_id=school.id, name="2026",
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        is_current=True, is_active=True,
    )
    student = Student(
        school_id=school.id, student_number="FEE-STU-001",
        first_name="Neo", last_name="Student", status="active", is_active=True,
    )
    db_session.add_all([year, student])
    db_session.commit()
    return school, year, student


def test_fee_charge_payment_balance_and_overpayment_protection(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school, year, student = _fee_setup(db_session)
    make_user(email="fees-admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("fees-admin@example.com", "StrongPass123")

    created = client.post(
        f"/api/v1/fees/charges?school_id={school.id}",
        headers=headers,
        json={
            "student_id": str(student.id),
            "academic_year_id": str(year.id),
            "description": "Term 3 tuition",
            "amount": "100.00",
        },
    )
    assert created.status_code == 201, created.text
    charge = created.json()
    assert charge["amount"] == 100.0
    assert charge["amount_paid"] == 0.0
    assert charge["balance"] == 100.0

    payment = client.post(
        f"/api/v1/fees/payments?school_id={school.id}",
        headers=headers,
        json={
            "charge_id": charge["id"],
            "payment_date": "2026-11-26",
            "amount": 40.0,
            "method": "cash",
            "reference": "FEE-REC-001",
        },
    )
    assert payment.status_code == 201, payment.text
    assert payment.json()["amount"] == 40.0

    listed = client.get(f"/api/v1/fees/charges?school_id={school.id}", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["amount_paid"] == 40.0
    assert listed.json()[0]["balance"] == 60.0

    overpayment = client.post(
        f"/api/v1/fees/payments?school_id={school.id}",
        headers=headers,
        json={
            "charge_id": charge["id"],
            "payment_date": "2026-11-26",
            "amount": 70.0,
            "method": "cash",
            "reference": "FEE-REC-002",
        },
    )
    assert overpayment.status_code == 409
    assert overpayment.json()["error"]["code"] == "PAYMENT_EXCEEDS_BALANCE"


def test_fee_payment_references_are_unique_within_a_school(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school, year, student = _fee_setup(db_session)
    make_user(email="fees-reference-admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("fees-reference-admin@example.com", "StrongPass123")
    charge = client.post(
        f"/api/v1/fees/charges?school_id={school.id}",
        headers=headers,
        json={
            "student_id": str(student.id),
            "academic_year_id": str(year.id),
            "description": "Registration",
            "amount": "200.00",
        },
    ).json()

    payload = {
        "charge_id": charge["id"], "payment_date": "2026-11-26",
        "amount": 25.0, "method": "mobile_money", "reference": "DUPLICATE-REF",
    }
    first = client.post(f"/api/v1/fees/payments?school_id={school.id}", headers=headers, json=payload)
    assert first.status_code == 201, first.text
    second = client.post(f"/api/v1/fees/payments?school_id={school.id}", headers=headers, json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DUPLICATE_PAYMENT_REFERENCE"


def test_teacher_cannot_access_school_fee_records(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    school, _year, _student = _fee_setup(db_session)
    make_user(email="fees-teacher@example.com", password="StrongPass123", role_name="TEACHER")
    headers = auth_headers("fees-teacher@example.com", "StrongPass123")
    response = client.get(f"/api/v1/fees/charges?school_id={school.id}", headers=headers)
    assert response.status_code == 403
