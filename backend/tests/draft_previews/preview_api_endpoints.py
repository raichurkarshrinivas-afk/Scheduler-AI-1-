def test_create_classroom_validation_and_list(client, fixture_data):
    headers = {"Authorization": f"Bearer {fixture_data['token_admin_a']}"}
    
    # 1. Invalid classroom: capacity 50, but rows 4 * cols 5 = 20 (< 50) -> should fail with 422
    res_invalid = client.post("/api/v1/facilities/classrooms", json={
        "name": "Invalid Grid Room",
        "building": "Engineering",
        "room_number": "E-101",
        "capacity": 50,
        "room_type": "LECTURE_HALL",
        "rows": 4,
        "columns": 5
    }, headers=headers)
    assert res_invalid.status_code == 422

    # 2. Valid classroom: capacity 30, rows 6 * cols 6 = 36 (>= 30)
    res_valid = client.post("/api/v1/facilities/classrooms", json={
        "name": "Robotics Lab",
        "building": "Engineering",
        "room_number": "E-202",
        "capacity": 30,
        "room_type": "COMPUTER_LAB",
        "rows": 6,
        "columns": 6
    }, headers=headers)
    assert res_valid.status_code == 201
    created_id = res_valid.json()["id"]

    # 3. List classrooms
    res_list = client.get("/api/v1/facilities/classrooms", headers=headers)
    assert res_list.status_code == 200
    ids = [r["id"] for r in res_list.json()]
    assert created_id in ids


def test_schedule_validation_and_creation(client, fixture_data):
    headers = {"Authorization": f"Bearer {fixture_data['token_admin_a']}"}

    payload = {
        "academic_term_id": fixture_data["term_a"].id,
        "course_id": fixture_data["course_cs101"].id,
        "batch_id": fixture_data["batch_cs1"].id,
        "instructor_id": fixture_data["instructor_a"].id,
        "classroom_id": fixture_data["room_lh1"].id,
        "time_slot_id": fixture_data["slot_mon1"].id
    }

    # First validate
    res_val = client.post("/api/v1/schedules/validate", json=payload, headers=headers)
    assert res_val.status_code == 200
    assert res_val.json()["is_valid"] is True

    # Create session
    res_create = client.post("/api/v1/schedules/sessions", json=payload, headers=headers)
    assert res_create.status_code == 201
    created_id = res_create.json()["id"]

    # Now attempt to book the SAME classroom and time slot for a different course -> 409 Conflict
    payload_conflict = {
        "academic_term_id": fixture_data["term_a"].id,
        "course_id": fixture_data["course_math201"].id,
        "batch_id": fixture_data["batch_cs1"].id,
        "instructor_id": fixture_data["instructor_a"].id,
        "classroom_id": fixture_data["room_lh1"].id,
        "time_slot_id": fixture_data["slot_mon1"].id
    }
    res_conflict = client.post("/api/v1/schedules/sessions", json=payload_conflict, headers=headers)
    assert res_conflict.status_code == 409


def test_exam_seating_lifecycle(client, fixture_data):
    admin_headers = {"Authorization": f"Bearer {fixture_data['token_admin_a']}"}
    student_headers = {"Authorization": f"Bearer {fixture_data['token_student_a1']}"}

    # 1. Create exam
    res_exam = client.post("/api/v1/seating/exams", json={
        "academic_term_id": fixture_data["term_a"].id,
        "name": "Final Semester Examination 2026",
        "exam_date": "2026-12-10",
        "time_slot_id": fixture_data["slot_mon1"].id
    }, headers=admin_headers)
    assert res_exam.status_code == 201
    exam_id = res_exam.json()["id"]

    # 2. Bulk enroll student_a1 and student_a2
    res_enroll = client.post(f"/api/v1/seating/exams/{exam_id}/enrollments", json={
        "enrollments": [
            {"student_id": fixture_data["student_a1"].id, "course_id": fixture_data["course_cs101"].id},
            {"student_id": fixture_data["student_a2"].id, "course_id": fixture_data["course_math201"].id}
        ]
    }, headers=admin_headers)
    assert res_enroll.status_code == 201

    # 3. Generate seating
    res_seating = client.post(f"/api/v1/seating/exams/{exam_id}/generate-seating", json={
        "classroom_ids": [fixture_data["room_lh1"].id]
    }, headers=admin_headers)
    assert res_seating.status_code == 200
    assert res_seating.json()["total_seated"] == 2

    # 4. Get visual report
    res_report = client.get(f"/api/v1/seating/exams/{exam_id}/report", headers=admin_headers)
    assert res_report.status_code == 200
    report_data = res_report.json()
    assert len(report_data["rooms"]) == 1
    assert report_data["rooms"][0]["occupied_seats"] == 2

    # 5. Student checks own hall ticket
    res_ticket = client.get(
        f"/api/v1/seating/exams/{exam_id}/hall-ticket/{fixture_data['student_a1'].id}",
        headers=student_headers
    )
    assert res_ticket.status_code == 200
    ticket = res_ticket.json()
    assert ticket["student_id"] == fixture_data["student_a1"].id
    assert "LH-101" in ticket["desk_label"]
