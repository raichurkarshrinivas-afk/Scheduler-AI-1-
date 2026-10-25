export type UserRole =
  | 'INSTITUTION_ADMINISTRATOR'
  | 'TIMETABLE_COORDINATOR'
  | 'EXAM_CONTROLLER'
  | 'TEACHER'
  | 'STUDENT';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  must_change_password: boolean;
  role: UserRole;
  institution_id: string;
  institution_name: string;
  institution_code: string;
  teacher_id?: string | null;
  student_id?: string | null;
  employee_id?: string | null;
  roll_number?: string | null;
}

// User alias for backward compatibility
export type User = UserProfile;

export interface SessionItem {
  id: string;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
  last_activity_at: string;
  expires_at: string;
  is_current: boolean;
}

export interface LoginResponse {
  user: UserProfile;
  csrf_token: string;
  must_change_password: boolean;
  message: string;
}

export interface Institution {
  id: string;
  name: string;
  code: string;
  timezone: string;
  is_active: boolean;
}

export interface Classroom {
  id: string;
  institution_id?: string;
  name: string;
  room_number: string;
  physical_capacity?: number;
  usable_exam_benches?: number;
  room_type?: string;
  building?: string;
  capacity?: number;
  rows: number;
  columns: number;
}

export interface AcademicTerm {
  id: string;
  institution_id: string;
  name: string;
  code: string;
  start_date: string;
  end_date: string;
  timezone: string;
  is_active: boolean;
}

export interface Department {
  id: string;
  institution_id: string;
  name: string;
  code: string;
}

export interface Subject {
  id: string;
  institution_id: string;
  department_id: string;
  code: string;
  name: string;
  subject_type: 'THEORY' | 'PRACTICAL' | 'INTEGRATED';
  credits: number;
}

// Backward compatibility types for legacy Phase 1 components
export interface Course {
  id: string;
  code: string;
  title?: string;
  name?: string;
  credits: number;
  department?: string;
  department_id?: string;
  course_type?: string;
  weekly_hours?: number;
  instructor_id: string;
  instructor_name?: string;
  preferred_room_type?: string;
}

export interface TimeSlot {
  id: string;
  day_of_week: 'MONDAY' | 'TUESDAY' | 'WEDNESDAY' | 'THURSDAY' | 'FRIDAY' | 'SATURDAY';
  start_time: string;
  end_time: string;
  slot_name?: string;
}

export interface ProgramBatch {
  id: string;
  name: string;
  department: string;
  semester: number;
  student_count: number;
}

export interface ScheduleSession {
  id: string;
  academic_term_id?: string;
  course_id: string;
  batch_id: string;
  classroom_id: string;
  timeslot_id?: string;
  time_slot_id?: string;
  day_of_week: string;
  start_time: string;
  end_time: string;
  instructor_id: string;
  instructor_name?: string;
  course_code?: string;
  course_title?: string;
  classroom_name?: string;
  batch_name?: string;
  status: 'DRAFT' | 'PUBLISHED';
}

export interface ConflictDetail {
  type: string;
  message: string;
  session_id?: string;
  entities?: string[];
}

export interface ExamSession {
  id: string;
  name: string;
  date?: string;
  exam_date?: string;
  start_time: string;
  end_time: string;
  course_ids: string[];
  status: 'DRAFT' | 'PUBLISHED';
}

export interface DeskCell {
  row: number;
  col: number;
  desk_label: string;
  is_occupied: boolean;
  student_id?: string;
  student_name?: string;
  course_code?: string;
}

export interface RoomSeatingPlan {
  classroom_id: string;
  classroom_name: string;
  room_number: string;
  building: string;
  rows: number;
  columns: number;
  total_seats: number;
  occupied_seats: number;
  grid: DeskCell[][];
}

export interface SeatingArrangementReport {
  exam_id: string;
  exam_name: string;
  date: string;
  start_time: string;
  end_time: string;
  rooms: RoomSeatingPlan[];
}

export type JobStatus = 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED';

export interface BackgroundJob {
  id: string;
  institution_id: string;
  job_type: string;
  input_reference: Record<string, any>;
  status: JobStatus;
  phase_label: string;
  attempt_count: number;
  max_attempts: number;
  available_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  elapsed_seconds?: number | null;
  lease_owner?: string | null;
  heartbeat_at?: string | null;
  result_reference?: Record<string, any> | null;
  error_code?: string | null;
  error_message?: string | null;
  cancellation_requested: boolean;
  created_at: string;
  updated_at: string;
}

export interface JobCancelResponse {
  job_id: string;
  status: string;
  cancellation_requested: boolean;
  message: string;
}

export interface TimetableAssignment {
  session_id: string;
  day: number;
  period: number;
  duration?: number;
  room_id: string;
  teacher_id?: string;
  section_id?: string;
  is_locked?: boolean;
}

export interface TimetableViolation {
  rule: string;
  session_id?: string;
  day?: number;
  period?: number;
  room_id?: string;
  message: string;
}

export interface TimetableValidationReport {
  is_valid: boolean;
  violations: TimetableViolation[];
  checked_at?: string;
  checker_version?: string;
}

export interface TimetableDraft {
  id: string;
  institution_id: string;
  academic_term_id: string;
  name: string;
  status: 'DRAFT' | 'GENERATING' | 'CHECKED' | 'INVALID' | 'REVIEWED' | 'PUBLISHED';
  revision: number;
  input_hash: string;
  input_snapshot: Record<string, any>;
  parameters: Record<string, any>;
  output_assignments: TimetableAssignment[];
  solver_status?: string | null;
  solver_runtime_seconds?: number | null;
  solver_objective?: number | null;
  solver_best_bound?: number | null;
  model_version: string;
  rule_version: string;
  checker_version: string;
  solver_version: string;
  validation_report?: TimetableValidationReport | null;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface AssignmentChange {
  session_id: string;
  session_name?: string;
  teacher_id?: string;
  section_id?: string;
  before: { day?: number; period?: number; room_id?: string };
  after: { day?: number; period?: number; room_id?: string };
  time_moved: boolean;
  room_changed: boolean;
  reason: string;
}

export interface RepairResponse {
  draft_id: string;
  revision: number;
  status: string;
  is_valid: boolean;
  changes: AssignmentChange[];
  change_count: number;
  validation_report?: TimetableValidationReport | null;
  output_assignments: TimetableAssignment[];
}


// ==========================================
// EXAM LOGISTICS TYPES (PHASE 9)
// ==========================================

export type ExamType = 'THEORY' | 'PRACTICAL';

export interface ExamSeat {
  id: string;
  row_num: number;
  col_num: number;
  bench_label: string;
  is_usable_for_exam: boolean;
  is_blocked?: boolean;
  is_accessible?: boolean;
  notes?: string;
}

export interface ExamRoom {
  id: string;
  name: string;
  code?: string;
  seats: ExamSeat[];
}

export interface ExamCandidate {
  id: string;
  roll_number: string;
  name: string;
  paper_id?: string;
  paper_code: string;
  paper_name?: string;
  batch_id?: string;
  requires_accessible_seat?: boolean;
  accessibility_notes?: string;
  private_accommodations?: string;
  required_os?: string;
  required_features?: string[];
}

export interface ExamTheoryAllocation {
  candidate_id: string;
  roll_number: string;
  name?: string;
  paper_code: string;
  room_id: string;
  seat_id: string;
  bench_label: string;
  row_num: number;
  col_num: number;
  is_accessible_seat?: boolean;
}

export interface Workstation {
  id: string;
  station_code: string;
  is_usable: boolean;
  os: string;
  installed_features: string[];
}

export interface PracticalLab {
  id: string;
  name: string;
  code?: string;
  effective_capacity_limit?: number;
  workstations: Workstation[];
}

export interface PracticalSittingConfig {
  batch_id: string;
  batch_name?: string;
  lab_id: string;
  start_time: string;
  duration_minutes: number;
  turnaround_buffer_minutes: number;
  examiner_id: string;
  assistant_id?: string;
}

export interface PracticalAllocation {
  candidate_id: string;
  roll_number: string;
  name?: string;
  batch_id: string;
  lab_id: string;
  workstation_id: string;
  station_code: string;
  os?: string;
  start_time?: string;
  duration_minutes?: number;
}

export interface ExamSitting {
  id: string;
  institution_id: string;
  academic_term_id: string;
  name: string;
  exam_type: ExamType;
  status: string; // 'DRAFT' | 'CHECKED' | 'PUBLISHED' | 'INVALID'
  revision: number;
  start_datetime?: string | null;
  duration_minutes: number;
  buffer_minutes: number;
  input_snapshot: {
    candidates?: ExamCandidate[];
    rooms?: ExamRoom[];
    labs?: PracticalLab[];
    sittings?: PracticalSittingConfig[];
    parameters?: Record<string, any>;
  };
  parameters: {
    hard_paper_adjacency?: boolean;
    batch_grouping_policy?: boolean;
    use_optimisation?: boolean;
    [key: string]: any;
  };
  output_allocations: (ExamTheoryAllocation | PracticalAllocation)[];
  validation_report?: {
    is_valid: boolean;
    violations: Array<{ code: string; message: string; [key: string]: any }>;
    warnings: Array<{ code: string; message: string; [key: string]: any }>;
    summary?: Record<string, any>;
    checker_version?: string;
  } | null;
  is_published: boolean;
  published_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExamSittingCreate {
  name: string;
  academic_term_id: string;
  exam_type?: ExamType;
  start_datetime?: string | null;
  duration_minutes?: number;
  buffer_minutes?: number;
  input_snapshot?: Record<string, any>;
  parameters?: Record<string, any>;
}

export interface SeatReassignRequest {
  expected_revision: number;
  seat_id?: string;
  room_id?: string;
  target_candidate_id?: string;
}

export interface WorkstationReassignRequest {
  expected_revision: number;
  batch_id?: string;
  lab_id?: string;
  workstation_id?: string;
}

export interface ExportData {
  document_type: string;
  sitting_id: string;
  sitting_name: string;
  academic_term_id: string;
  exam_type: string;
  status_label: string;
  revision: number;
  generated_at: string;
  export_token: string;
  expires_at: string;
  seats?: any[];
  candidates?: any[];
  allocations?: any[];
  [key: string]: any;
}


// ==========================================
// PHASE 10: CONTROLLED PUBLICATION & STUDENT VIEW TYPES
// ==========================================

export interface PrePublishReview {
  can_publish: boolean;
  draft_id: string;
  revision: number;
  validation_report: {
    is_valid: boolean;
    violations: Array<{ code: string; message: string; [key: string]: any }>;
    warnings: Array<{ code: string; message: string; [key: string]: any }>;
    checker_version?: string;
  };
  changed_sessions_count: number;
  affected_teachers_count: number;
  affected_students_count: number;
  unmet_preferences_count: number;
  warnings: Array<{ code?: string; message: string; [key: string]: any }>;
  potential_reservation_conflicts: Array<{
    resource_id: string;
    day: number;
    period: number;
    conflicting_publication_id: string;
    session_title?: string;
  }>;
  previous_active_version?: number | null;
}

export interface PublishRequest {
  draft_id: string;
  publication_type: 'TIMETABLE' | 'EXAM_THEORY' | 'EXAM_PRACTICAL';
  expected_revision: number;
  publication_note?: string;
}

export interface Publication {
  id: string;
  institution_id: string;
  academic_term_id: string;
  publication_type: string;
  source_id: string;
  version_number: number;
  published_by_user_id: string;
  publication_note: string;
  published_at: string;
  snapshot: Record<string, any>;
  diff_summary: Record<string, any>;
  checker_report: Record<string, any>;
  is_active: boolean;
  created_at: string;
}

export interface PublicationSummary {
  id: string;
  publication_type: string;
  version_number: number;
  published_at: string;
  publication_note: string;
  is_active: boolean;
  publisher_name?: string | null;
  change_count: number;
}

export interface PublicationDiff {
  source_version: number;
  target_version: number;
  changed_sessions: Array<{
    session_id: string;
    session_name?: string;
    before: { day?: number; period?: number; room_id?: string };
    after: { day?: number; period?: number; room_id?: string };
  }>;
  added_sessions: any[];
  removed_sessions: any[];
  affected_teachers: string[];
  affected_sections: string[];
}

export interface StudentProfile {
  student_id: string;
  user_id: string;
  roll_number: string;
  full_name: string;
  email: string;
  department_name?: string | null;
  admission_year: number;
  is_active: boolean;
}

export interface DatedOccurrence {
  session_id: string;
  title: string;
  subject_code: string;
  subject_name?: string | null;
  section_name?: string | null;
  date: string;
  day_of_week: number;
  period: number;
  start_time: string;
  end_time: string;
  room_name: string;
  building_name?: string | null;
  teacher_name: string;
  is_cancelled: boolean;
  cancellation_reason?: string | null;
  term_timezone: string;
}

export interface StudentTimetableResponse {
  is_published: boolean;
  academic_term_id?: string | null;
  term_name?: string | null;
  term_timezone: string;
  week_start_date: string;
  occurrences: DatedOccurrence[];
  calendar_exceptions: Array<{ date: string; type: string; description: string }>;
  publication_version?: number | null;
  publication_note?: string | null;
}

export interface StudentExamSeat {
  sitting_id: string;
  exam_name: string;
  paper_code: string;
  paper_name?: string | null;
  start_datetime?: string | null;
  duration_minutes: number;
  hall_name: string;
  bench_label: string;
  row_num: number;
  col_num: number;
  is_accessible: boolean;
  accessibility_notes?: string | null;
}

export interface StudentPractical {
  sitting_id: string;
  exam_name: string;
  lab_name: string;
  station_code: string;
  os?: string | null;
  installed_features: string[];
  batch_name: string;
  start_time: string;
  duration_minutes: number;
  turnaround_buffer_minutes: number;
  examiner_name?: string | null;
}

export interface StudentChangeNotice {
  id: string;
  published_at: string;
  version_number: number;
  event_type: string;
  note: string;
  summary: Record<string, any>;
}

export interface StudentHomeData {
  profile: StudentProfile;
  is_published: boolean;
  next_up?: DatedOccurrence | null;
  today_schedule: DatedOccurrence[];
  upcoming_exams: StudentExamSeat[];
  practical_sessions: StudentPractical[];
  recent_changes: StudentChangeNotice[];
  publication_version?: number | null;
}


// Phase 11 Communication & Calendar Types
export type NotificationCategory = 'ACADEMIC_CHANGE' | 'OPERATIONAL_ALERT' | 'SECURITY_EVENT' | 'SCHEDULED_REMINDER';
export type NotificationPriority = 'URGENT' | 'NORMAL' | 'LOW';

export interface AppNotification {
  id: string;
  institution_id: string;
  recipient_user_id: string;
  category: NotificationCategory;
  priority: NotificationPriority;
  title: string;
  message: string;
  data: Record<string, any>;
  is_read: boolean;
  read_at?: string | null;
  scheduled_for?: string | null;
  delivered_at?: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: AppNotification[];
  total: number;
  unread_count: number;
}

export interface NotificationPreferences {
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  notify_academic_changes: boolean;
  notify_operational_alerts: boolean;
  notify_security_events: boolean;
  notify_scheduled_reminders: boolean;
  email_notifications_enabled: boolean;
  calendar_sync_enabled: boolean;
}

export interface OutboxEvent {
  id: string;
  institution_id: string;
  publication_id?: string | null;
  event_type: string;
  recipient_role: string;
  payload: Record<string, any>;
  status: 'PENDING' | 'DISPATCHED' | 'FAILED';
  retry_count: number;
  max_retries: number;
  last_error?: string | null;
  next_retry_at?: string | null;
  processed_at?: string | null;
  created_at: string;
}

export interface CalendarStatus {
  configured: boolean;
  status: 'NOT_CONFIGURED' | 'CONNECTED' | 'DISCONNECTED' | 'REVOKED';
  is_connected: boolean;
  calendar_id?: string | null;
  sync_event_count: number;
  last_synced_at?: string | null;
  last_error?: string | null;
  guidance?: string | null;
}


// ============================================================================
// PHASE 12: FEEDBACK AND CONTACT TYPES
// ============================================================================

export type FeedbackStatus =
  | 'new'
  | 'reviewing'
  | 'awaiting_information'
  | 'resolved'
  | 'closed';

export type PublicFeedbackCategory =
  | 'GENERAL_INQUIRY'
  | 'PILOT_REQUEST'
  | 'BUG_REPORT'
  | 'ACCESSIBILITY'
  | 'OTHER';

export type AuthenticatedFeedbackCategory =
  | 'BUG_REPORT'
  | 'SUGGESTION'
  | 'ACCESS_ISSUE'
  | 'SCHEDULING_ISSUE'
  | 'OTHER';

export interface PublicContactPayload {
  name?: string;
  email?: string;
  category: PublicFeedbackCategory | string;
  subject: string;
  message: string;
  honeypot?: string;
}

export interface PublicContactResponse {
  success: boolean;
  reference_code: string;
  message: string;
}

export interface AuthenticatedFeedbackPayload {
  category: AuthenticatedFeedbackCategory | string;
  subject: string;
  message: string;
  page_reference?: string;
}

export interface AuthenticatedFeedbackResponse {
  success: boolean;
  reference_code: string;
  message: string;
  submission: {
    id: string;
    reference_code: string;
    category: string;
    subject: string;
    message: string;
    page_reference?: string | null;
    status: FeedbackStatus;
    created_at: string;
  };
}

export interface UserSubmittedFeedback {
  id: string;
  reference_code: string;
  category: string;
  subject: string;
  message: string;
  page_reference?: string | null;
  status: FeedbackStatus;
  created_at: string;
  updated_at: string;
}

export interface FeedbackInternalNote {
  id: string;
  author_user_id: string;
  author_name: string;
  note: string;
  created_at: string;
}

export interface FeedbackManageItem {
  id: string;
  reference_code: string;
  institution_id?: string | null;
  submitting_user_id?: string | null;
  submitting_user_name?: string | null;
  submitting_user_role?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  category: string;
  subject: string;
  message: string;
  page_reference?: string | null;
  status: FeedbackStatus;
  assigned_reviewer_id?: string | null;
  assigned_reviewer_name?: string | null;
  notes_count: number;
  created_at: string;
  updated_at: string;
}

export interface FeedbackDetailItem extends FeedbackManageItem {
  internal_notes: FeedbackInternalNote[];
}

export interface FeedbackManageResponse {
  items: FeedbackManageItem[];
  total: number;
}

// ============================================================================
// PHASE 13: OPTIONAL AI-ASSISTED INTERPRETATION TYPES
// ============================================================================

export type AmbiguityType =
  | 'UNDEFINED_TIME'
  | 'UNKNOWN_ENTITY'
  | 'PREFERENCE_VS_HARD_CONSTRAINT'
  | 'TERM_WIDE_VS_DATE_SPECIFIC'
  | 'OTHER';

export interface AmbiguityFlag {
  type: AmbiguityType;
  description: string;
  suggested_clarification: string;
}

export interface AIStatusOut {
  enabled: boolean;
  provider: string;
  is_available: boolean;
  model_name: string;
  total_requests: number;
  total_tokens: number;
  estimated_cost_usd: number;
  disclaimer: string;
}

export interface ResolvedSessionChange {
  session_id: string;
  session_name: string;
  course_code: string;
  original_day: number;
  original_period: number;
  original_room_id?: string | null;
  original_room_name?: string | null;
  original_teacher_id?: string | null;
  original_teacher_name?: string | null;
  proposed_day: number;
  proposed_period: number;
  proposed_room_id?: string | null;
  proposed_room_name?: string | null;
  proposed_teacher_id?: string | null;
  proposed_teacher_name?: string | null;
  is_hard_constraint: boolean;
  is_term_wide: boolean;
  is_resolved: boolean;
  resolution_notes: string[];
}

export interface TimetableInterpretationResponse {
  success: boolean;
  raw_summary: string;
  confidence_score: number;
  is_ambiguous: boolean;
  ambiguities: AmbiguityFlag[];
  proposed_changes: ResolvedSessionChange[];
  draft_id: string;
  draft_revision: number;
  disclaimer: string;
}

export interface ApplyInterpretedChangesOut {
  success: boolean;
  draft_id: string;
  new_revision: number;
  applied_count: number;
  checker_report: Record<string, any>;
  status: string;
  message: string;
}

export interface CheckerIssueExplanation {
  rule: string;
  summary: string;
  root_cause_explanation: string;
  potential_resolutions: string[];
  involved_sessions: string[];
  involved_resources: string[];
}

export interface ExplainCheckerIssuesOut {
  success: boolean;
  explanations: CheckerIssueExplanation[];
  general_recommendations: string[];
  disclaimer: string;
}

export interface ColumnMappingProposalOut {
  success: boolean;
  mappings: Record<string, string | null>;
  confidences: Record<string, number>;
  ambiguities: string[];
  unmapped_headers: string[];
  disclaimer: string;
}
