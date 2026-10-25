# Solver Benchmark Script
# Records hardware, fixture size, parameters and actual measurements.
# Strictly separate from normal API throughput benchmarks.

import time
import tracemalloc
import json
import platform
from app.services.schedule_solver import ScheduleSolver
from app.services.schedule_checker import ScheduleChecker

hw = {
    'cpu': 'AMD Ryzen 7 260 w/ Radeon 780M (8 Cores, 16 Logical Processors)',
    'ram_gb': 24,
    'os': f'{platform.system()} {platform.release()} (Build {platform.version()})',
    'python_version': platform.python_version(),
}

def make_fix(ns, nt, nr, nd=5, np=8):
    rooms = [{'id': f'r_{i}', 'name': f'Room {100+i}', 'capacity': 45} for i in range(nr)]
    teachers = [{'id': f't_{i}', 'name': f'Instructor {i}'} for i in range(nt)]
    sections = [{'id': f'sec_{i}', 'name': f'Cohort {i}'} for i in range(max(1, nt // 2))]
    sessions = [{'id': f's_{i}', 'name': f'Module {i}', 'teacher_id': f't_{i % nt}', 'section_id': f'sec_{i % len(sections)}', 'duration': 1, 'capacity_needed': 30} for i in range(ns)]
    return {'days': list(range(nd)), 'periods_per_day': np, 'break_periods': [3], 'rooms': rooms, 'teachers': teachers, 'sections': sections, 'sessions': sessions, 'rules': {'consecutive_lecture_limit': 3}}

def bench(name, fix, tl=15.0):
    tracemalloc.start()
    t0 = time.perf_counter()
    res = ScheduleSolver.solve(fix, time_limit_seconds=tl)
    elapsed = time.perf_counter() - t0
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assigns = res.get('assignments', [])
    chk = ScheduleChecker.validate(fix, assigns)
    return {
        'benchmark_name': name,
        'num_sessions': len(fix['sessions']),
        'num_teachers': len(fix['teachers']),
        'num_rooms': len(fix['rooms']),
        'total_slots': len(fix['days']) * fix['periods_per_day'],
        'status': res.get('solver_status'),
        'wall_time_seconds': round(elapsed, 4),
        'solver_reported_runtime': res.get('runtime_seconds'),
        'objective_value': res.get('objective_value'),
        'best_bound': res.get('best_bound'),
        'assigned_count': len(assigns),
        'peak_memory_mb': round(peak / (1024 * 1024), 2),
        'independent_checker_valid': chk.get('is_valid', False),
        'checker_violations_count': len(chk.get('violations', [])),
    }

def main():
    results = []
    results.append(bench('Small Instance (12 Sessions)', make_fix(12, 4, 4, 5, 6), 10.0))
    results.append(bench('Medium Instance (36 Sessions)', make_fix(36, 10, 8, 5, 7), 15.0))
    results.append(bench('Large Instance (80 Sessions)', make_fix(80, 20, 15, 5, 8), 20.0))
    results.append(bench('Infeasible Boundary (Pigeonhole Violation)', make_fix(10, 1, 5, 1, 4), 5.0))
    out = {'hardware': hw, 'results': results}
    with open('scripts/solver_benchmark_results.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)
    print('Benchmark finished successfully.')

if __name__ == '__main__':
    main()
