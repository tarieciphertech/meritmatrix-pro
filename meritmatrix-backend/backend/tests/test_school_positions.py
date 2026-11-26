"""School position permissions and multi-position assignment tests."""


def test_school_positions_grant_school_scoped_permissions_and_combine_positions(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    from app.models.school import School
    from app.models.staff import Staff
    from app.models.user_school import UserSchool

    school = School(name="Position RBAC School", code="POSRBAC1", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()

    headmaster_user = make_user(
        email="headmaster.position@example.com", password="StrongPass123", role_name="SCHOOL_STAFF"
    )
    clerk_user = make_user(
        email="clerk.position@example.com", password="StrongPass123", role_name="SCHOOL_STAFF"
    )
    headmaster = Staff(
        school_id=school.id, staff_number="POS-HM-01", first_name="Head", last_name="Master",
        user_id=headmaster_user.id, employment_status="active", is_active=True,
    )
    clerk = Staff(
        school_id=school.id, staff_number="POS-CL-01", first_name="School", last_name="Clerk",
        user_id=clerk_user.id, employment_status="active", is_active=True,
    )
    db_session.add_all([headmaster, clerk])
    db_session.flush()
    db_session.add_all([
        UserSchool(user_id=headmaster_user.id, school_id=school.id, school_role="SCHOOL_STAFF"),
        UserSchool(user_id=clerk_user.id, school_id=school.id, school_role="SCHOOL_STAFF"),
    ])
    db_session.commit()

    make_user(email="position-platform-admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    platform_headers = auth_headers("position-platform-admin@example.com", "StrongPass123")
    positions_response = client.get(
        "/api/v1/school-positions", headers=platform_headers, params={"school_id": str(school.id)}
    )
    assert positions_response.status_code == 200, positions_response.text
    positions = {row["code"]: row for row in positions_response.json()}

    headmaster_assignment = client.put(
        f"/api/v1/school-positions/staff/{headmaster.id}",
        headers=platform_headers,
        params={"school_id": str(school.id)},
        json={"position_ids": [positions["HEADMASTER"]["id"]]},
    )
    assert headmaster_assignment.status_code == 200, headmaster_assignment.text

    clerk_assignment = client.put(
        f"/api/v1/school-positions/staff/{clerk.id}",
        headers=platform_headers,
        params={"school_id": str(school.id)},
        json={"position_ids": [positions["SCHOOL_CLERK"]["id"], positions["SCHOOL_SECRETARY"]["id"]]},
    )
    assert clerk_assignment.status_code == 200, clerk_assignment.text
    assert {p["code"] for p in clerk_assignment.json()["positions"]} == {"SCHOOL_CLERK", "SCHOOL_SECRETARY"}

    headmaster_headers = auth_headers("headmaster.position@example.com", "StrongPass123")
    clerk_headers = auth_headers("clerk.position@example.com", "StrongPass123")

    # Headmaster receives full school-level staff administration rights.
    created_staff = client.post(
        "/api/v1/staff",
        headers=headmaster_headers,
        params={"school_id": str(school.id)},
        json={"staff_number": "POS-NEW-01", "first_name": "New", "last_name": "Employee"},
    )
    assert created_staff.status_code == 201, created_staff.text

    # Clerk can read the staff directory but cannot create staff records.
    staff_list = client.get(
        "/api/v1/staff", headers=clerk_headers, params={"school_id": str(school.id)}
    )
    assert staff_list.status_code == 200, staff_list.text
    denied_staff_create = client.post(
        "/api/v1/staff",
        headers=clerk_headers,
        params={"school_id": str(school.id)},
        json={"staff_number": "POS-DENY-01", "first_name": "Not", "last_name": "Allowed"},
    )
    assert denied_staff_create.status_code == 403
    assert denied_staff_create.json()["error"]["code"] == "PERMISSION_DENIED"

    # Clerk can capture payments, but cannot create new fee charges.
    payments = client.get(
        "/api/v1/fees/payments", headers=clerk_headers, params={"school_id": str(school.id)}
    )
    assert payments.status_code == 200, payments.text
    denied_charge = client.post(
        "/api/v1/fees/charges",
        headers=clerk_headers,
        params={"school_id": str(school.id)},
        json={
            "student_id": "00000000-0000-0000-0000-000000000001",
            "academic_year_id": "00000000-0000-0000-0000-000000000002",
            "description": "Unauthorized charge",
            "amount": "100.00",
        },
    )
    assert denied_charge.status_code == 403
    assert denied_charge.json()["error"]["code"] == "PERMISSION_DENIED"
    payment_capture = client.post(
        "/api/v1/fees/payments",
        headers=clerk_headers,
        params={"school_id": str(school.id)},
        json={
            "charge_id": "00000000-0000-0000-0000-000000000003",
            "payment_date": "2026-11-26",
            "amount": 10.00,
            "method": "cash",
        },
    )
    assert payment_capture.status_code == 404
    assert payment_capture.json()["error"]["code"] == "FEE_CHARGE_NOT_FOUND"
