# Representative API Throughput & Latency Load Tests
# Measures actual performance for:
# 1. Student published reads
# 2. Login under controlled conditions
# 3. Publication workflow
# 4. Job submission
# Records hardware, parameters, p50, p95, p99 latencies, and real req/sec throughput.

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import time
import json
import statistics
import platform
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.academic import AcademicTerm
from app.models.schedule import TimetableDraft
from app.seeds.seed import run_seed

hw = {
    "cpu": "AMD Ryzen 7 260 w/ Radeon 780M (8 Cores, 16 Logical Processors)",
    "ram_gb": 24,
    "os": f"{platform.system()} {platform.release()} (Build {platform.version()})",
    "python_version": platform.python_version(),
}

def benchmark_endpoint(name, func, iterations=50):
    latencies_ms = []
    successes = 0
    failures = 0

    t_start = time.perf_counter()
    for _ in range(iterations):
        t0 = time.perf_counter()
        try:
            status_ok = func()
            lat_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(lat_ms)
            if status_ok:
                successes += 1
            else:
                failures += 1
        except Exception as ex:
            failures += 1
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

    total_time = time.perf_counter() - t_start
    latencies_ms.sort()

    p50 = statistics.median(latencies_ms)
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)] if latencies_ms else 0.0
    p99 = latencies_ms[int(len(latencies_ms) * 0.99)] if latencies_ms else 0.0
    rps = round(iterations / total_time, 2) if total_time > 0 else 0.0

    return {
        "endpoint_benchmark": name,
        "iterations": iterations,
        "total_time_seconds": round(total_time, 4),
        "throughput_req_per_sec": rps,
        "p50_latency_ms": round(p50, 2),
        "p95_latency_ms": round(p95, 2),
        "p99_latency_ms": round(p99, 2),
        "mean_latency_ms": round(statistics.mean(latencies_ms), 2),
        "min_latency_ms": round(min(latencies_ms), 2),
        "max_latency_ms": round(max(latencies_ms), 2),
        "success_rate_percent": round((successes / iterations) * 100.0, 1),
    }

def main():
    print("===========================================================")
    print("          API THROUGHPUT & LATENCY LOAD BENCHMARKS         ")
    print("===========================================================")
    print(f"Hardware: {hw['cpu']} | {hw['ram_gb']} GB RAM")
    print("===========================================================")

    db = SessionLocal()
    run_seed(db)
    term = db.query(AcademicTerm).first()
    db.close()

    results = []

    # 1. Login under controlled conditions (Argon2id password verification)
    login_client = TestClient(app, base_url="http://testserver")
    def test_login():
        resp = login_client.post("/api/v1/auth/login", json={
            "institution_code": "APEX",
            "identifier": "coord@apex.edu",
            "password": "DevSeed2026!#",
        })
        return resp.status_code == 200

    r_login = benchmark_endpoint("Login (Argon2id Password Verification)", test_login, iterations=40)
    results.append(r_login)
    print(f"[LOGIN]      Throughput: {r_login['throughput_req_per_sec']} req/s | p50: {r_login['p50_latency_ms']}ms | p95: {r_login['p95_latency_ms']}ms | Success: {r_login['success_rate_percent']}%")

    # 2. Student Published Reads (High-traffic read endpoint)
    student_client = TestClient(app, base_url="http://testserver")
    stu_login = student_client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "alice@apex.edu",
        "password": "DevSeed2026!#",
    })
    assert stu_login.status_code == 200, stu_login.text
    student_csrf = stu_login.json()["csrf_token"]

    def test_student_read():
        resp = student_client.get("/api/v1/student/timetable", headers={"X-CSRF-Token": student_csrf})
        return resp.status_code in (200, 404)

    r_student = benchmark_endpoint("Student Published Timetable Read", test_student_read, iterations=100)
    results.append(r_student)
    print(f"[STUDENT]    Throughput: {r_student['throughput_req_per_sec']} req/s | p50: {r_student['p50_latency_ms']}ms | p95: {r_student['p95_latency_ms']}ms | Success: {r_student['success_rate_percent']}%")

    # 3. Job Submission (Durable queue insertion with validation)
    coord_client = TestClient(app, base_url="http://testserver")
    coord_login = coord_client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "coord@apex.edu",
        "password": "DevSeed2026!#",
    })
    assert coord_login.status_code == 200, coord_login.text
    coord_csrf = coord_login.json()["csrf_token"]
    coord_headers = {"X-CSRF-Token": coord_csrf}

    def test_job_submission():
        resp = coord_client.post("/api/v1/jobs", json={
            "job_type": "GENERIC_TASK",
            "input_reference": {"test": "load_test_job"},
            "max_attempts": 3,
        }, headers=coord_headers)
        return resp.status_code == 201

    r_jobs = benchmark_endpoint("Job Submission to Durable Queue", test_job_submission, iterations=60)
    results.append(r_jobs)
    print(f"[JOB QUEUE]  Throughput: {r_jobs['throughput_req_per_sec']} req/s | p50: {r_jobs['p50_latency_ms']}ms | p95: {r_jobs['p95_latency_ms']}ms | Success: {r_jobs['success_rate_percent']}%")

    # 4. Publication Pre-Publish Review Analysis
    draft_resp = coord_client.post("/api/v1/timetable-drafts", json={
        "name": "Load Test Draft",
        "academic_term_id": term.id,
        "input_snapshot": {
            "sessions": [{"id": "s1", "name": "Lecture 1", "teacher_id": "t1", "section_id": "sec1"}],
            "rooms": [{"id": "r1", "name": "Room 1", "capacity": 40}],
            "teachers": [{"id": "t1", "name": "Prof T"}],
            "sections": [{"id": "sec1", "name": "Sec 1"}],
        },
    }, headers=coord_headers)
    assert draft_resp.status_code == 201, draft_resp.text
    draft_id = draft_resp.json()["id"]

    def test_publication_review():
        resp = coord_client.get(f"/api/v1/publications/pre-publish-review/{draft_id}", headers=coord_headers)
        return resp.status_code == 200

    r_pub = benchmark_endpoint("Pre-Publication Verification & Diff Review", test_publication_review, iterations=40)
    results.append(r_pub)
    print(f"[PUB REVIEW] Throughput: {r_pub['throughput_req_per_sec']} req/s | p50: {r_pub['p50_latency_ms']}ms | p95: {r_pub['p95_latency_ms']}ms | Success: {r_pub['success_rate_percent']}%")

    out = {"hardware": hw, "results": results}
    with open("scripts/load_test_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("Load test completed and saved to scripts/load_test_results.json")

if __name__ == "__main__":
    main()
