import { UserProfile, LoginResponse } from '../types';

export const MOCK_USERS: Record<string, UserProfile> = {
  'admin@apex.edu': {
    id: 'user-admin-1',
    email: 'admin@apex.edu',
    full_name: 'Dr. Eleanor Vance (Administrator)',
    must_change_password: false,
    role: 'INSTITUTION_ADMINISTRATOR',
    institution_id: 'inst-apex-1',
    institution_name: 'Apex Institute of Technology',
    institution_code: 'APEX',
    employee_id: 'EMP-ADM-001',
  },
  'teacher@apex.edu': {
    id: 'user-teacher-1',
    email: 'teacher@apex.edu',
    full_name: 'Prof. Marcus Thorne (Faculty)',
    must_change_password: false,
    role: 'TEACHER',
    institution_id: 'inst-apex-1',
    institution_name: 'Apex Institute of Technology',
    institution_code: 'APEX',
    teacher_id: 'tea-apex-01',
    employee_id: 'FAC-CS-042',
  },
  'APEX-STU-2026-001': {
    id: 'user-student-1',
    email: 'aarav.sharma@apex.edu',
    full_name: 'Aarav Sharma (Student)',
    must_change_password: false,
    role: 'STUDENT',
    institution_id: 'inst-apex-1',
    institution_name: 'Apex Institute of Technology',
    institution_code: 'APEX',
    student_id: 'stu-apex-101',
    roll_number: 'APEX-STU-2026-001',
  },
};

export const getMockLoginResponse = (identifier: string): LoginResponse => {
  const cleanId = identifier.trim().toLowerCase();
  const matched =
    cleanId.includes('admin') ? MOCK_USERS['admin@apex.edu'] :
    cleanId.includes('teach') || cleanId.includes('fac') ? MOCK_USERS['teacher@apex.edu'] :
    cleanId.includes('stu') ? MOCK_USERS['APEX-STU-2026-001'] :
    MOCK_USERS['admin@apex.edu'];

  return {
    user: matched,
    csrf_token: 'mock-demo-csrf-token-xyz',
    must_change_password: false,
    message: 'Authenticated in interactive Vercel demo mode',
  };
};

export const MOCK_SESSIONS = [
  {
    id: 'sess-1',
    day_of_week: 1, // Monday
    start_time: '09:00',
    end_time: '10:30',
    course_name: 'Distributed Systems & Cloud Computing',
    course_code: 'CS-401',
    room_number: 'LH-101',
    building: 'Turing Hall',
    instructor_name: 'Prof. Marcus Thorne',
    session_type: 'THEORY',
    status: 'SCHEDULED',
    section_name: 'Section A',
  },
  {
    id: 'sess-2',
    day_of_week: 1, // Monday
    start_time: '11:00',
    end_time: '13:00',
    course_name: 'Operating Systems Kernel Laboratory',
    course_code: 'CS-302-LAB',
    room_number: 'LAB-B',
    building: 'Von Neumann Block',
    instructor_name: 'Dr. Sarah Lin',
    session_type: 'PRACTICAL',
    status: 'SCHEDULED',
    section_name: 'Batch B1',
  },
  {
    id: 'sess-3',
    day_of_week: 2, // Tuesday
    start_time: '10:00',
    end_time: '11:30',
    course_name: 'Advanced Database Internals & Storage',
    course_code: 'CS-305',
    room_number: 'LH-204',
    building: 'Turing Hall',
    instructor_name: 'Prof. Marcus Thorne',
    session_type: 'THEORY',
    status: 'SCHEDULED',
    section_name: 'Section A',
  },
  {
    id: 'sess-4',
    day_of_week: 3, // Wednesday
    start_time: '14:00',
    end_time: '15:30',
    course_name: 'Computer Networks & Security',
    course_code: 'CS-308',
    room_number: 'LH-102',
    building: 'Lovelace Wing',
    instructor_name: 'Dr. Robert Miller',
    session_type: 'THEORY',
    status: 'SCHEDULED',
    section_name: 'Section A',
  },
  {
    id: 'sess-5',
    day_of_week: 4, // Thursday
    start_time: '09:30',
    end_time: '11:00',
    course_name: 'Distributed Systems & Cloud Computing',
    course_code: 'CS-401',
    room_number: 'LH-101',
    building: 'Turing Hall',
    instructor_name: 'Prof. Marcus Thorne',
    session_type: 'THEORY',
    status: 'SCHEDULED',
    section_name: 'Section A',
  },
  {
    id: 'sess-6',
    day_of_week: 5, // Friday
    start_time: '11:00',
    end_time: '12:30',
    course_name: 'Compiler Design & Optimization',
    course_code: 'CS-405',
    room_number: 'LH-201',
    building: 'Turing Hall',
    instructor_name: 'Dr. Sarah Lin',
    session_type: 'THEORY',
    status: 'SCHEDULED',
    section_name: 'Section A',
  },
];

export const MOCK_EXAM_SEATING = [
  {
    exam_id: 'exam-midterm-1',
    subject_name: 'Distributed Systems (CS-401)',
    exam_date: '2026-11-12',
    start_time: '10:00',
    end_time: '13:00',
    room_number: 'Exam Hall 101',
    building: 'Academic Block A',
    bench_number: 'A-14',
    anti_cheating_status: 'ISOLATED_OK',
    guidelines: 'Single candidate per bench. Carry student ID card.',
  },
  {
    exam_id: 'exam-midterm-2',
    subject_name: 'Database Internals (CS-305)',
    exam_date: '2026-11-15',
    start_time: '14:00',
    end_time: '17:00',
    room_number: 'Exam Hall 204',
    building: 'Academic Block B',
    bench_number: 'B-08',
    anti_cheating_status: 'ISOLATED_OK',
    guidelines: 'Single candidate per bench. Calculators prohibited.',
  },
];
