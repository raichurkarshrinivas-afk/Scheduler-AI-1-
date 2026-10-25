def test_institution_data_isolation_classrooms(client, fixture_data):
    # Admin A requests classrooms -> sees room_lh1 from Alpha only
    headers_a = {"Authorization": f"Bearer {fixture_data['token_admin_a']}"}
    res_a = client.get("/api/v1/facilities/classrooms", headers=headers_a)
    assert res_a.status_code == 200
    rooms_a = res_a.json()
    assert len(rooms_a) == 1
    assert rooms_a[0]["id"] == fixture_data["room_lh1"].id

    # Admin B requests classrooms -> sees room_beta from Beta only
    headers_b = {"Authorization": f"Bearer {fixture_data['token_admin_b']}"}
    res_b = client.get("/api/v1/facilities/classrooms", headers=headers_b)
    assert res_b.status_code == 200
    rooms_b = res_b.json()
    assert len(rooms_b) == 1
    assert rooms_b[0]["id"] == "room-beta-1"


def test_cross_institution_deletion_blocked(client, fixture_data):
    # Admin A attempts to delete a classroom belonging to Institution Beta
    headers_a = {"Authorization": f"Bearer {fixture_data['token_admin_a']}"}
    res = client.delete("/api/v1/facilities/classrooms/room-beta-1", headers=headers_a)
    # Must return 404 to avoid leaking existence across tenants
    assert res.status_code == 404


def test_role_enforcement_student_forbidden_to_create_classroom(client, fixture_data):
    # Student A attempts to create a classroom
    headers_student = {"Authorization": f"Bearer {fixture_data['token_student_a1']}"}
    res = client.post("/api/v1/facilities/classrooms", json={
        "name": "Unauthorized Room",
        "building": "Main",
        "room_number": "999",
        "capacity": 20,
        "room_type": "LECTURE_HALL",
        "rows": 4,
        "columns": 5
    }, headers=headers_student)
    assert res.status_code == 403
