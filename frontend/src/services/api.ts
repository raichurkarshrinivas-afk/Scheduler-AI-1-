import {
  UserProfile,
  SessionItem,
  LoginResponse,
  SeatingArrangementReport,
  Classroom,
  Course,
  ScheduleSession,
  ConflictDetail,
  BackgroundJob,
  JobCancelResponse,
  TimetableDraft,
  RepairResponse,
  ExamSitting,
  ExamSittingCreate,
  SeatReassignRequest,
  WorkstationReassignRequest,
  ExportData,
  PrePublishReview,
  PublishRequest,
  Publication,
  PublicationSummary,
  PublicationDiff,
  StudentProfile,
  StudentTimetableResponse,
  StudentExamSeat,
  StudentPractical,
  StudentChangeNotice,
  AppNotification,
  NotificationListResponse,
  NotificationPreferences,
  OutboxEvent,
  CalendarStatus,
  StudentHomeData,
  PublicContactPayload,
  PublicContactResponse,
  AuthenticatedFeedbackPayload,
  AuthenticatedFeedbackResponse,
  UserSubmittedFeedback,
  FeedbackDetailItem,
  FeedbackManageResponse,
  FeedbackInternalNote,
  FeedbackStatus,
  AIStatusOut,
  ResolvedSessionChange,
  TimetableInterpretationResponse,
  ApplyInterpretedChangesOut,
  ExplainCheckerIssuesOut,
  ColumnMappingProposalOut,
} from '../types';

import { getMockLoginResponse, MOCK_USERS, MOCK_SESSIONS, MOCK_EXAM_SEATING } from './mockData';

const API_BASE = '/api/v1';

let demoUser: UserProfile | null = (() => {
  try {
    const saved = localStorage.getItem('scheduler_demo_user');
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
})();

function handleMockFallback<T>(endpoint: string, options: RequestInit = {}): T {
  const method = (options.method || 'GET').toUpperCase();
  let body: any = {};
  try {
    body = options.body ? JSON.parse(options.body as string) : {};
  } catch {}

  if (endpoint.includes('/auth/login') && method === 'POST') {
    const res = getMockLoginResponse(body.identifier || 'admin@apex.edu');
    demoUser = res.user;
    try { localStorage.setItem('scheduler_demo_user', JSON.stringify(demoUser)); } catch {}
    return res as unknown as T;
  }

  if (endpoint === '/me') {
    if (demoUser) return demoUser as unknown as T;
    const defaultUser = MOCK_USERS['admin@apex.edu'];
    demoUser = defaultUser;
    try { localStorage.setItem('scheduler_demo_user', JSON.stringify(demoUser)); } catch {}
    return defaultUser as unknown as T;
  }

  if (endpoint.includes('/auth/logout')) {
    demoUser = null;
    try { localStorage.removeItem('scheduler_demo_user'); } catch {}
    return {} as unknown as T;
  }

  if (endpoint.includes('/sessions') || endpoint.includes('/timetable')) {
    return MOCK_SESSIONS as unknown as T;
  }

  if (endpoint.includes('/seating') || endpoint.includes('/exams')) {
    return MOCK_EXAM_SEATING as unknown as T;
  }

  return [] as unknown as T;
}

// In-memory CSRF token store (never store credentials in localStorage!)
let memoryCsrfToken: string | null = null;

export const setCsrfToken = (token: string | null) => {
  memoryCsrfToken = token;
};

export const getCsrfToken = (): string | null => {
  if (memoryCsrfToken) return memoryCsrfToken;
  // Fallback: attempt to read from scheduler_csrf cookie
  const match = document.cookie.match(/(^|;)\s*scheduler_csrf=([^;]+)/);
  if (match) {
    return decodeURIComponent(match[2]);
  }
  return null;
};

async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');

  const method = (options.method || 'GET').toUpperCase();
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      headers.set('X-CSRF-Token', csrf);
    }
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      credentials: 'include',
    });

    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');

    if (!response.ok || !isJson) {
      if (response.status === 404 || !isJson || response.status === 502) {
        return handleMockFallback<T>(endpoint, options);
      }

      if (
        response.status === 403 &&
        response.headers.get('X-Error-Code') === 'PASSWORD_CHANGE_REQUIRED'
      ) {
        window.dispatchEvent(new CustomEvent('auth:password-change-required'));
      }

      if (response.status === 401) {
        window.dispatchEvent(new CustomEvent('auth:session-expired'));
      }

      const errorBody = await response.json().catch(() => ({}));
      const message = errorBody.detail?.message || errorBody.detail || 'An unexpected error occurred.';
      throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  } catch {
    return handleMockFallback<T>(endpoint, options);
  }
}

export const api = {
  // Phase 3 Authentication & Session Management
  auth: {
    login: async (credentials: {
      institution_code: string;
      identifier: string;
      password: string;
    }): Promise<LoginResponse> => {
      const res = await apiFetch<LoginResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials),
      });
      if (res.csrf_token) {
        setCsrfToken(res.csrf_token);
      }
      return res;
    },

    logout: async (): Promise<void> => {
      await apiFetch<void>('/auth/logout', { method: 'POST' });
      setCsrfToken(null);
    },

    changePassword: async (data: {
      current_password: string;
      new_password: string;
    }): Promise<{ detail: string }> => {
      return apiFetch<{ detail: string }>('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    getMe: async (): Promise<UserProfile> => {
      return apiFetch<UserProfile>('/me');
    },

    getSessions: async (): Promise<SessionItem[]> => {
      return apiFetch<SessionItem[]>('/me/sessions');
    },

    revokeSession: async (sessionId: string): Promise<{ detail: string }> => {
      return apiFetch<{ detail: string }>(`/me/sessions/${sessionId}`, {
        method: 'DELETE',
      });
    },

    adminResetPassword: async (
      userId: string,
      data: { temporary_password?: string }
    ): Promise<{ user_id: string; temporary_password: string; must_change_password: boolean }> => {
      return apiFetch(`/admin/users/${userId}/reset-password`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },
  },

  students: {
    getStudent: async (id: string) => {
      return apiFetch<any>(`/students/${id}`);
    },
  },

  // Backward compatibility wrappers for Phase 1 legacy mock pages
  getSeatingReport: async (examId: string): Promise<SeatingArrangementReport> => {
    return apiFetch<SeatingArrangementReport>(`/exams/${examId}/seating`);
  },

  generateSeating: async (examId: string, rooms: string[]): Promise<any> => {
    return apiFetch(`/exams/${examId}/generate-seating`, {
      method: 'POST',
      body: JSON.stringify({ rooms }),
    });
  },

  getHallTicket: async (examId: string, studentId: string): Promise<any> => {
    return apiFetch(`/exams/${examId}/hall-ticket/${studentId}`);
  },

  createClassroom: async (data: Partial<Classroom>): Promise<Classroom> => {
    return apiFetch<Classroom>('/classrooms', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  createCourse: async (data: Partial<Course>): Promise<Course> => {
    return apiFetch<Course>('/courses', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  validateSchedule: async (data: any): Promise<{ valid: boolean; conflicts: ConflictDetail[] }> => {
    return apiFetch<{ valid: boolean; conflicts: ConflictDetail[] }>('/schedule/validate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  createSession: async (data: Partial<ScheduleSession>): Promise<ScheduleSession> => {
    return apiFetch<ScheduleSession>('/schedule/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  deleteSession: async (id: string): Promise<void> => {
    return apiFetch<void>(`/schedule/sessions/${id}`, {
      method: 'DELETE',
    });
  },

  timetableDrafts: {
    create: (data: { name: string; academic_term_id: string; input_snapshot?: any; parameters?: any }) =>
      apiFetch<TimetableDraft>('/timetable-drafts', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    get: (id: string) => apiFetch<TimetableDraft>(`/timetable-drafts/${id}`),
    generate: (id: string, params?: { time_limit_seconds?: number; num_workers?: number }) =>
      apiFetch<{ draft_id: string; job_id: string; status: string; message: string }>(
        `/timetable-drafts/${id}/generate`,
        { method: 'POST', body: JSON.stringify(params || {}) }
      ),
    check: (id: string) =>
      apiFetch<{ is_valid: boolean; violations: any[]; checker_version: string }>(
        `/timetable-drafts/${id}/check`,
        { method: 'POST' }
      ),
    updateAssignment: (
      draftId: string,
      assignmentId: string,
      data: {
        expected_revision: number;
        day?: number;
        period?: number;
        room_id?: string;
        is_locked?: boolean;
      }
    ) =>
      apiFetch<TimetableDraft>(`/timetable-drafts/${draftId}/assignments/${assignmentId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    repair: (
      draftId: string,
      data: { expected_revision: number; time_limit_seconds?: number }
    ) =>
      apiFetch<RepairResponse>(`/timetable-drafts/${draftId}/repair`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  jobs: {
    getJob: (id: string) => apiFetch<BackgroundJob>(`/jobs/${id}`),
    cancelJob: (id: string) =>
      apiFetch<JobCancelResponse>(`/jobs/${id}/cancel`, { method: 'POST' }),
    listJobs: (statusFilter?: string) => {
      const q = statusFilter ? `?status_filter=${statusFilter}` : '';
      return apiFetch<BackgroundJob[]>(`/jobs${q}`);
    },
    enqueueJob: (
      jobType: string,
      inputRef: Record<string, any> = {},
      maxAttempts: number = 3
    ) =>
      apiFetch<BackgroundJob>('/jobs', {
        method: 'POST',
        body: JSON.stringify({
          job_type: jobType,
          input_reference: inputRef,
          max_attempts: maxAttempts,
        }),
      }),
  },

  exams: {
    listSittings: (examType?: string, academicTermId?: string) => {
      const params = new URLSearchParams();
      if (examType) params.append('exam_type', examType);
      if (academicTermId) params.append('academic_term_id', academicTermId);
      const q = params.toString() ? `?${params.toString()}` : '';
      return apiFetch<ExamSitting[]>(`/exams/sittings${q}`);
    },
    getSitting: (id: string, examType: 'THEORY' | 'PRACTICAL' = 'THEORY') =>
      apiFetch<ExamSitting>(`/exams/${examType.toLowerCase()}/sittings/${id}`),
    createTheorySitting: (data: ExamSittingCreate) =>
      apiFetch<ExamSitting>('/exams/theory/sittings', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    allocateTheorySeating: (id: string) =>
      apiFetch<ExamSitting>(`/exams/theory/sittings/${id}/allocate`, {
        method: 'POST',
      }),
    validateTheorySeating: (id: string) =>
      apiFetch<any>(`/exams/theory/sittings/${id}/validate`, {
        method: 'POST',
      }),
    reassignTheorySeat: (
      id: string,
      candidateId: string,
      data: SeatReassignRequest
    ) =>
      apiFetch<ExamSitting>(
        `/exams/theory/sittings/${id}/seats/${candidateId}`,
        {
          method: 'PATCH',
          body: JSON.stringify(data),
        }
      ),
    createPracticalSitting: (data: ExamSittingCreate) =>
      apiFetch<ExamSitting>('/exams/practical/sittings', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    allocatePracticalWorkstations: (id: string) =>
      apiFetch<ExamSitting>(`/exams/practical/sittings/${id}/allocate`, {
        method: 'POST',
      }),
    validatePracticalAllocation: (id: string) =>
      apiFetch<any>(`/exams/practical/sittings/${id}/validate`, {
        method: 'POST',
      }),
    reassignPracticalWorkstation: (
      id: string,
      candidateId: string,
      data: WorkstationReassignRequest
    ) =>
      apiFetch<ExamSitting>(
        `/exams/practical/sittings/${id}/workstations/${candidateId}`,
        {
          method: 'PATCH',
          body: JSON.stringify(data),
        }
      ),
    exportSeatPlan: (id: string, roomId?: string) => {
      const q = roomId ? `?room_id=${roomId}` : '';
      return apiFetch<ExportData>(`/exams/theory/sittings/${id}/export/seat-plan${q}`);
    },
    exportCandidateList: (id: string) =>
      apiFetch<ExportData>(`/exams/theory/sittings/${id}/export/candidate-list`),
    exportAttendanceSheet: (id: string, roomId?: string) => {
      const q = roomId ? `?room_id=${roomId}` : '';
      return apiFetch<ExportData>(`/exams/theory/sittings/${id}/export/attendance-sheet${q}`);
    },
    exportPracticalWorkstations: (id: string) =>
      apiFetch<ExportData>(`/exams/practical/sittings/${id}/export/workstation-list`),
  },

  publications: {
    getPrePublishReview: (draftId: string) =>
      apiFetch<PrePublishReview>(`/publications/pre-publish-review/${draftId}`),
    publish: (data: PublishRequest) =>
      apiFetch<Publication>('/publications/publish', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    list: (publicationType?: string, academicTermId?: string) => {
      const p = new URLSearchParams();
      if (publicationType) p.append('publication_type', publicationType);
      if (academicTermId) p.append('academic_term_id', academicTermId);
      const q = p.toString() ? `?${p.toString()}` : '';
      return apiFetch<PublicationSummary[]>(`/publications${q}`);
    },
    get: (id: string) => apiFetch<Publication>(`/publications/${id}`),
    getDiff: (id: string, compareId: string) =>
      apiFetch<PublicationDiff>(`/publications/${id}/diff/${compareId}`),
    restore: (id: string) =>
      apiFetch<TimetableDraft>(`/publications/${id}/restore`, { method: 'POST' }),
  },

  communication: {
    getNotifications: (params?: { category?: string; unread_only?: boolean; limit?: number; offset?: number }) => {
      const p = new URLSearchParams();
      if (params?.category) p.append('category', params.category);
      if (params?.unread_only) p.append('unread_only', 'true');
      if (params?.limit) p.append('limit', String(params.limit));
      if (params?.offset) p.append('offset', String(params.offset));
      const q = p.toString() ? `?${p.toString()}` : '';
      return apiFetch<NotificationListResponse>(`/communication/notifications${q}`);
    },
    getUnreadCount: () => apiFetch<{ unread_count: number }>('/communication/notifications/unread-count'),
    markRead: (id: string) => apiFetch<AppNotification>(`/communication/notifications/${id}/read`, { method: 'POST' }),
    markAllRead: () => apiFetch<{ marked_count: number }>('/communication/notifications/mark-all-read', { method: 'POST' }),
    getPreferences: () => apiFetch<NotificationPreferences>('/communication/preferences'),
    updatePreferences: (data: Partial<NotificationPreferences>) =>
      apiFetch<NotificationPreferences>('/communication/preferences', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    getOutbox: (statusFilter?: string) => {
      const q = statusFilter ? `?status=${statusFilter}` : '';
      return apiFetch<OutboxEvent[]>(`/communication/outbox${q}`);
    },
    retryOutbox: (id: string) => apiFetch<OutboxEvent>(`/communication/outbox/${id}/retry`, { method: 'POST' }),
    getCalendarStatus: () => apiFetch<CalendarStatus>('/communication/calendar/status'),
    getCalendarAuthUrl: () => apiFetch<{ auth_url: string; state: string }>('/communication/calendar/auth-url'),
    syncCalendar: () => apiFetch<{ synced: boolean; count?: number; error?: string }>('/communication/calendar/sync', { method: 'POST' }),
    disconnectCalendar: () => apiFetch<{ disconnected: boolean }>('/communication/calendar/disconnect', { method: 'POST' }),
    pollEvents: (since: number = 0) => apiFetch<{ events: any[] }>(`/communication/events/poll?since=${since}`),
  },

  student: {
    getMe: () => apiFetch<StudentProfile>('/student/me'),
    getHome: () => apiFetch<StudentHomeData>('/student/home'),
    getTimetable: (weekStartDate?: string) => {
      const q = weekStartDate ? `?week_start_date=${weekStartDate}` : '';
      return apiFetch<StudentTimetableResponse>(`/student/timetable${q}`);
    },
    getExams: () => apiFetch<StudentExamSeat[]>('/student/exams'),
    getPracticals: () => apiFetch<StudentPractical[]>('/student/practicals'),
    getRecentChanges: () => apiFetch<StudentChangeNotice[]>('/student/recent-changes'),
    changePassword: (data: { current_password: string; new_password: string }) =>
      apiFetch<{ message: string }>('/student/change-password', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },


  feedback: {
    submitPublic: (payload: PublicContactPayload) =>
      apiFetch<PublicContactResponse>('/feedback/public', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    submitAuthenticated: (payload: AuthenticatedFeedbackPayload) =>
      apiFetch<AuthenticatedFeedbackResponse>('/feedback/submit', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    getMySubmissions: () =>
      apiFetch<UserSubmittedFeedback[]>('/feedback/my-submissions'),
    getManageList: (params?: {
      status?: string;
      category?: string;
      search?: string;
      include_public?: boolean;
      limit?: number;
      offset?: number;
    }) => {
      const p = new URLSearchParams();
      if (params?.status) p.append('status', params.status);
      if (params?.category) p.append('category', params.category);
      if (params?.search) p.append('search', params.search);
      if (params?.include_public !== undefined) p.append('include_public', String(params.include_public));
      if (params?.limit) p.append('limit', String(params.limit));
      if (params?.offset) p.append('offset', String(params.offset));
      const q = p.toString() ? ('?' + p.toString()) : '';
      return apiFetch<FeedbackManageResponse>('/feedback/manage' + q);
    },
    getManageDetail: (id: string) =>
      apiFetch<FeedbackDetailItem>('/feedback/manage/' + id),
    updateStatus: (
      id: string,
      data: {
        status: FeedbackStatus;
        assigned_reviewer_id?: string | null;
        internal_note?: string | null;
      }
    ) =>
      apiFetch<{ success: boolean; status: FeedbackStatus; assigned_reviewer_id?: string | null; updated_at: string }>(
        '/feedback/manage/' + id + '/status',
        {
          method: 'PUT',
          body: JSON.stringify(data),
        }
      ),
    addInternalNote: (id: string, note: string) =>
      apiFetch<FeedbackInternalNote>('/feedback/manage/' + id + '/notes', {
        method: 'POST',
        body: JSON.stringify({ note }),
      }),
  },

  ai: {
    getStatus: () => apiFetch<AIStatusOut>('/ai/status'),
    interpretChange: (data: { draft_id: string; request_text: string }) =>
      apiFetch<TimetableInterpretationResponse>('/ai/interpret-change', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    applyChange: (data: {
      draft_id: string;
      expected_revision: number;
      changes: ResolvedSessionChange[];
    }) =>
      apiFetch<ApplyInterpretedChangesOut>('/ai/apply-change', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    explainChecker: (data: { draft_id: string; violations?: any[] }) =>
      apiFetch<ExplainCheckerIssuesOut>('/ai/explain-checker', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    proposeMappings: (data: { headers: string[]; sample_rows?: string[][] }) =>
      apiFetch<ColumnMappingProposalOut>('/ai/propose-mappings', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
};
