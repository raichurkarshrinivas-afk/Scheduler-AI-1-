import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  CheckCircle2,
  XCircle,
  Eye,
  EyeOff,
  ArrowLeft,
} from 'lucide-react';
import { api } from './services/api';
import { UserProfile, SessionItem } from './types';
import { LandingPage } from './pages/LandingPage';
import { StaffLayout } from './components/layout/StaffLayout';
import { StudentLayout } from './components/layout/StudentLayout';
import { StaffOverview } from './pages/staff/StaffOverview';
import { StaffTimetables } from './pages/staff/StaffTimetables';
import { StaffExaminations } from './pages/staff/StaffExaminations';
import { StaffResources } from './pages/staff/StaffResources';
import { StaffPublishHistory } from './pages/staff/StaffPublishHistory';
import { StaffReports } from './pages/staff/StaffReports';
import { StaffFeedback } from './pages/staff/StaffFeedback';
import { StaffSettings } from './pages/staff/StaffSettings';
import { StudentHome } from './pages/student/StudentHome';
import { StudentTimetable } from './pages/student/StudentTimetable';
import { StudentPracticals } from './pages/student/StudentPracticals';
import { StudentExamsSeats } from './pages/student/StudentExamsSeats';
import { StudentNotifications } from './pages/student/StudentNotifications';
import { StudentProfile } from './pages/student/StudentProfile';
import { StudentFeedback } from './pages/student/StudentFeedback';
import { NotificationCenterModal } from './components/communication/NotificationCenterModal';
import { useSSE } from './hooks/useSSE';
import { Dialog } from './components/common/Dialog';
import { Button } from './components/common/Button';
import { FormField, Input } from './components/common/FormField';
import { StatusBadge } from './components/common/StatusBadge';

export const App: React.FC = () => {
  const queryClient = useQueryClient();

  // Navigation & Shell State
  const [viewMode, setViewMode] = useState<'landing' | 'login' | 'app'>('landing');
  const [activeStaffPath, setActiveStaffPath] = useState<string>('overview');
  const [activeStudentPath, setActiveStudentPath] = useState<string>('home');
  const [activeTerm, setActiveTerm] = useState<string>('Autumn 2026');

  // Modal Dialogs
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);
  const [isManageSessionsOpen, setIsManageSessionsOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isAdminGuidanceOpen, setIsAdminGuidanceOpen] = useState(false);

  // Authentication Credentials
  const [institutionCode, setInstitutionCode] = useState<string>('APEX');
  const [identifier, setIdentifier] = useState<string>('admin@apex.edu');
  const [password, setPassword] = useState<string>('DevSeed2026!#');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [sessionExpiredNotice, setSessionExpiredNotice] = useState<boolean>(false);

  // Password Change State
  const [currentPassword, setCurrentPassword] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [changePasswordError, setChangePasswordError] = useState<string | null>(null);
  const [changePasswordSuccess, setChangePasswordSuccess] = useState<boolean>(false);

  // 1. Initial Authentication Check (/api/v1/me)
  const {
    data: currentUser,
    refetch: refetchUser,
  } = useQuery<UserProfile | null>({
    queryKey: ['current-user'],
    queryFn: async () => {
      try {
        return await api.auth.getMe();
      } catch {
        return null;
      }
    },
    retry: false,
    staleTime: 60000,
  });

  // Phase 11: Real-time SSE Connection & Polling Fallback
  const { isConnected: isSSEConnected, fallbackMode: isSSEFallback } = useSSE({
    enabled: !!currentUser,
    onNotificationNew: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-notifications-count'] });
    },
    onPublicationUpdated: () => {
      queryClient.invalidateQueries({ queryKey: ['publications'] });
      queryClient.invalidateQueries({ queryKey: ['student-recent-changes'] });
      queryClient.invalidateQueries({ queryKey: ['student-timetable'] });
      queryClient.invalidateQueries({ queryKey: ['student-exams'] });
    },
  });

  // Real-time Unread Notifications Count Query
  const { data: unreadData } = useQuery({
    queryKey: ['unread-notifications-count'],
    queryFn: () => api.communication.getUnreadCount(),
    enabled: !!currentUser,
    refetchInterval: isSSEConnected ? 60000 : 15000,
  });
  const unreadNotificationsCount = unreadData?.unread_count ?? 0;

  // Switch to app shell if authenticated
  useEffect(() => {
    if (currentUser) {
      setViewMode('app');
    }
  }, [currentUser]);

  // Handle Session Expiration & Password Change Requirement Events
  useEffect(() => {
    const handleExpired = () => {
      setSessionExpiredNotice(true);
      setViewMode('login');
      queryClient.setQueryData(['current-user'], null);
    };

    const handlePasswordChangeRequired = () => {
      setIsChangePasswordOpen(true);
    };

    window.addEventListener('auth:session-expired', handleExpired);
    window.addEventListener('auth:password-change-required', handlePasswordChangeRequired);

    return () => {
      window.removeEventListener('auth:session-expired', handleExpired);
      window.removeEventListener('auth:password-change-required', handlePasswordChangeRequired);
    };
  }, [queryClient]);

  // 2. Login Mutation
  const loginMutation = useMutation({
    mutationFn: () =>
      api.auth.login({
        institution_code: institutionCode.trim(),
        identifier: identifier.trim(),
        password: password,
      }),
    onSuccess: (data) => {
      setLoginError(null);
      setSessionExpiredNotice(false);
      queryClient.setQueryData(['current-user'], data.user);
      if (data.must_change_password) {
        setIsChangePasswordOpen(true);
      }
      setViewMode('app');
      refetchUser();
    },
    onError: (err: any) => {
      setLoginError(err.message || 'Invalid credentials or login failed.');
    },
  });

  // 3. Logout Mutation
  const logoutMutation = useMutation({
    mutationFn: () => api.auth.logout(),
    onSuccess: () => {
      queryClient.clear();
      queryClient.setQueryData(['current-user'], null);
      setViewMode('landing');
    },
  });

  // 4. Change Password Mutation
  const changePasswordMutation = useMutation({
    mutationFn: () =>
      api.auth.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    onSuccess: () => {
      setChangePasswordError(null);
      setChangePasswordSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      refetchUser();
      setTimeout(() => {
        setIsChangePasswordOpen(false);
        setChangePasswordSuccess(false);
      }, 1500);
    },
    onError: (err: any) => {
      setChangePasswordError(err.message || 'Password change failed.');
    },
  });

  // Active Sessions Query
  const { data: activeSessions, refetch: refetchSessions } = useQuery<SessionItem[]>({
    queryKey: ['active-sessions'],
    queryFn: () => api.auth.getSessions(),
    enabled: isManageSessionsOpen,
  });

  const revokeSessionMutation = useMutation({
    mutationFn: (sessionId: string) => api.auth.revokeSession(sessionId),
    onSuccess: () => {
      refetchSessions();
    },
  });

  // Quick Account Switcher Helper
  const fillCredentials = (code: string, ident: string, pass: string) => {
    setInstitutionCode(code);
    setIdentifier(ident);
    setPassword(pass);
    setLoginError(null);
  };

  // Password Policy Checks
  const passwordChecks = [
    { label: 'At least 10 characters', met: newPassword.length >= 10 },
    { label: 'One uppercase letter (A-Z)', met: /[A-Z]/.test(newPassword) },
    { label: 'One lowercase letter (a-z)', met: /[a-z]/.test(newPassword) },
    { label: 'One digit (0-9)', met: /[0-9]/.test(newPassword) },
    { label: 'One special symbol (!@#$%^&*)', met: /[^A-Za-z0-9]/.test(newPassword) },
  ];
  const isPasswordValid = passwordChecks.every((c) => c.met);

  // -------------------------------------------------------------
  // VIEW MODE: PUBLIC LANDING PAGE
  // -------------------------------------------------------------
  if (viewMode === 'landing') {
    return <LandingPage onLoginClick={() => setViewMode('login')} />;
  }

  // -------------------------------------------------------------
  // VIEW MODE: AUTHENTICATION / LOGIN PAGE
  // -------------------------------------------------------------
  if (viewMode === 'login' || !currentUser) {
    return (
      <div className="min-h-screen bg-bg flex flex-col justify-between selection:bg-teal-light selection:text-teal">
        {/* Top Header */}
        <header className="h-16 border-b border-border bg-white px-4 sm:px-8 flex items-center justify-between">
          <button
            type="button"
            onClick={() => setViewMode('landing')}
            className="flex items-center gap-2 text-xs font-semibold text-navy-muted hover:text-navy transition-colors focus-visible:outline-2 focus-visible:outline-teal rounded p-1"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Public Website</span>
          </button>

          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-teal text-white flex items-center justify-center font-bold font-heading text-sm shadow-subtle">
              S
            </div>
            <span className="font-heading font-bold text-sm text-navy">Scheduler</span>
          </div>
        </header>

        {/* Main Login Card */}
        <main className="flex-1 flex items-center justify-center p-4 py-12">
          <div className="w-full max-w-md bg-white border border-border rounded-2xl shadow-elevated p-6 sm:p-8 space-y-6">
            <div className="text-center space-y-1">
              <h1 className="font-heading text-2xl font-bold text-navy">
                Institutional Sign In
              </h1>
              <p className="text-xs text-navy-muted">
                Server-side browser session with cryptographic verification.
              </p>
            </div>

            {sessionExpiredNotice && (
              <div className="p-3 rounded-lg bg-amber-light border border-amber/30 text-xs text-amber-900 flex items-start gap-2" role="alert">
                <AlertCircle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                <span>Your previous session has expired. Please log in again.</span>
              </div>
            )}

            {loginError && (
              <div className="p-3 rounded-lg bg-coral-light border border-coral/30 text-xs text-coral flex items-start gap-2" role="alert">
                <AlertCircle className="w-4 h-4 text-coral shrink-0 mt-0.5" />
                <span>{loginError}</span>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                loginMutation.mutate();
              }}
              className="space-y-4"
            >
              <FormField label="Institution Code" htmlFor="inst-code" required>
                <Input
                  id="inst-code"
                  placeholder="e.g. APEX or BEACON"
                  value={institutionCode}
                  onChange={(e) => setInstitutionCode(e.target.value.toUpperCase())}
                  required
                />
              </FormField>

              <FormField
                label="Login Identifier"
                htmlFor="user-ident"
                helperText="Email, Teacher Employee ID, or Student PRN"
                required
              >
                <Input
                  id="user-ident"
                  placeholder="admin@apex.edu or APEX-FAC-101"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  required
                />
              </FormField>

              <FormField label="Password" htmlFor="user-pass" required>
                <div className="relative">
                  <Input
                    id="user-pass"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter account password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-navy-subtle hover:text-navy focus-visible:outline-2 focus-visible:outline-teal rounded"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </FormField>

              <Button
                type="submit"
                variant="primary"
                size="md"
                className="w-full"
                isLoading={loginMutation.isPending}
                id="submit-login-btn"
              >
                Sign In to Workspace
              </Button>
            </form>

            {/* Quick-Switch Demo Accounts */}
            <div className="pt-4 border-t border-border">
              <span className="text-[11px] font-semibold text-navy-subtle uppercase tracking-wider block mb-2 text-center">
                Quick Demo Switcher
              </span>
              <div className="grid grid-cols-2 gap-1.5 text-xs">
                <button
                  type="button"
                  onClick={() => fillCredentials('APEX', 'admin@apex.edu', 'DevSeed2026!#')}
                  className="p-1.5 rounded border border-border bg-bg hover:bg-border/50 text-left truncate"
                >
                  <strong className="block text-navy">Administrator</strong>
                  <span className="text-[10px] text-navy-subtle truncate block">admin@apex.edu</span>
                </button>

                <button
                  type="button"
                  onClick={() => fillCredentials('APEX', 'coord@apex.edu', 'DevSeed2026!#')}
                  className="p-1.5 rounded border border-border bg-bg hover:bg-border/50 text-left truncate"
                >
                  <strong className="block text-navy">Coordinator</strong>
                  <span className="text-[10px] text-navy-subtle truncate block">coord@apex.edu</span>
                </button>

                <button
                  type="button"
                  onClick={() => fillCredentials('APEX', 'APEX-FAC-101', 'DevSeed2026!#')}
                  className="p-1.5 rounded border border-border bg-bg hover:bg-border/50 text-left truncate"
                >
                  <strong className="block text-navy">Teacher (Faculty ID)</strong>
                  <span className="text-[10px] text-navy-subtle truncate block">APEX-FAC-101</span>
                </button>

                <button
                  type="button"
                  onClick={() => fillCredentials('APEX', 'APEX-STU-2026-001', 'DevSeed2026!#')}
                  className="p-1.5 rounded border border-border bg-bg hover:bg-border/50 text-left truncate"
                >
                  <strong className="block text-navy">Student (PRN)</strong>
                  <span className="text-[10px] text-teal truncate block font-medium">APEX-STU-2026-001</span>
                </button>
              </div>
            </div>

            {/* Administrative Reset Guidance Notice */}
            <div className="pt-2 text-center">
              <button
                type="button"
                onClick={() => setIsAdminGuidanceOpen(true)}
                className="text-xs text-navy-subtle hover:text-navy underline focus-visible:outline-2 focus-visible:outline-teal rounded"
              >
                Forgotten credentials or temporary password?
              </button>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="py-4 text-center text-xs text-navy-subtle border-t border-border bg-white">
          <span>&copy; {new Date().getFullYear()} Scheduler &bull; Single-Instance In-Memory Sliding Window Throttled</span>
        </footer>

        {/* Administrative Reset Guidance Modal */}
        <Dialog
          isOpen={isAdminGuidanceOpen}
          onClose={() => setIsAdminGuidanceOpen(false)}
          title="Administrative Credential Recovery Guidance"
          footer={<Button variant="primary" size="sm" onClick={() => setIsAdminGuidanceOpen(false)}>Understood</Button>}
        >
          <div className="space-y-3 text-xs text-navy-muted leading-relaxed">
            <p>
              To maintain academic integrity and prevent email-based account takeover, <strong>public self-service password recovery is disabled</strong>.
            </p>
            <p>
              If you have lost access to your account or require temporary credentials:
            </p>
            <ol className="list-decimal pl-5 space-y-1.5 text-navy">
              <li>Contact your institutional IT department or Timetable Coordinator.</li>
              <li>An authorized Administrator will generate temporary credentials using the internal admin reset workflow.</li>
              <li>Upon your next login, you will be automatically prompted to configure a new personal password.</li>
            </ol>
          </div>
        </Dialog>
      </div>
    );
  }

  // -------------------------------------------------------------
  // VIEW MODE: AUTHENTICATED APPLICATION SHELL
  // -------------------------------------------------------------
  const isStudent = currentUser.role === 'STUDENT';

  return (
    <>
      {isStudent ? (
        <StudentLayout
          user={currentUser}
          activePath={activeStudentPath}
          onNavigate={setActiveStudentPath}
          activeTerm={activeTerm}
          onTermChange={setActiveTerm}
          onLogout={() => logoutMutation.mutate()}
          onChangePasswordClick={() => setIsChangePasswordOpen(true)}
          onManageSessionsClick={() => setIsManageSessionsOpen(true)}
          onNotificationsClick={() => setIsNotificationsOpen(true)}
          unreadNotificationsCount={unreadNotificationsCount}
        >
          {activeStudentPath === 'home' && (
            <StudentHome user={currentUser} onNavigate={setActiveStudentPath} />
          )}
          {activeStudentPath === 'timetable' && <StudentTimetable />}
          {activeStudentPath === 'practicals' && <StudentPracticals />}
          {activeStudentPath === 'exams-seats' && <StudentExamsSeats user={currentUser} />}
          {activeStudentPath === 'notifications' && <StudentNotifications />}
          {activeStudentPath === 'feedback' && <StudentFeedback />}
          {activeStudentPath === 'profile' && (
            <StudentProfile
              user={currentUser}
              onChangePasswordClick={() => setIsChangePasswordOpen(true)}
            />
          )}
        </StudentLayout>
      ) : (
        <StaffLayout
          user={currentUser}
          activePath={activeStaffPath}
          onNavigate={setActiveStaffPath}
          activeTerm={activeTerm}
          onTermChange={setActiveTerm}
          onLogout={() => logoutMutation.mutate()}
          onChangePasswordClick={() => setIsChangePasswordOpen(true)}
          onManageSessionsClick={() => setIsManageSessionsOpen(true)}
          onNotificationsClick={() => setIsNotificationsOpen(true)}
          unreadNotificationsCount={unreadNotificationsCount}
        >
          {activeStaffPath === 'overview' && (
            <StaffOverview user={currentUser} onNavigate={setActiveStaffPath} />
          )}
          {activeStaffPath === 'timetables' && <StaffTimetables />}
          {activeStaffPath === 'examinations' && <StaffExaminations />}
          {activeStaffPath === 'resources' && <StaffResources />}
          {activeStaffPath === 'publish-history' && <StaffPublishHistory />}
          {activeStaffPath === 'reports' && <StaffReports />}
          {activeStaffPath === 'feedback' && <StaffFeedback />}
          {activeStaffPath === 'settings' && <StaffSettings user={currentUser} />}
        </StaffLayout>
      )}

      {/* ------------------------------------------------------------- */}
      {/* GLOBAL MODALS (CHANGE PASSWORD, ACTIVE SESSIONS, NOTIFICATIONS) */}
      {/* ------------------------------------------------------------- */}

      {/* Change Password Dialog (Enforced or On-Demand) */}
      <Dialog
        isOpen={isChangePasswordOpen || currentUser?.must_change_password}
        onClose={() => {
          if (!currentUser?.must_change_password) {
            setIsChangePasswordOpen(false);
          }
        }}
        title={
          currentUser?.must_change_password
            ? 'First-Time Password Change Required'
            : 'Change Account Password'
        }
        description="Password must contain at least 10 characters, mixed case, numbers, and symbols."
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (newPassword === confirmPassword && isPasswordValid) {
              changePasswordMutation.mutate();
            }
          }}
          className="space-y-4"
        >
          {changePasswordError && (
            <div className="p-3 rounded-lg bg-coral-light border border-coral/30 text-xs text-coral" role="alert">
              {changePasswordError}
            </div>
          )}

          {changePasswordSuccess && (
            <div className="p-3 rounded-lg bg-teal-light border border-teal/30 text-xs text-teal font-semibold">
              &check; Password changed successfully! Rotating sessions...
            </div>
          )}

          <FormField label="Current Password" htmlFor="curr-pass" required>
            <Input
              id="curr-pass"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </FormField>

          <FormField label="New Secure Password" htmlFor="new-pass" required>
            <Input
              id="new-pass"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </FormField>

          {/* Real-time Password Complexity Checklist */}
          <div className="p-3 rounded-lg bg-bg border border-border space-y-1.5 text-xs select-none">
            <span className="font-semibold text-navy block text-[11px] uppercase tracking-wider">
              Password Complexity Requirements:
            </span>
            {passwordChecks.map((check, idx) => (
              <div key={idx} className="flex items-center gap-2">
                {check.met ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-teal shrink-0" aria-hidden="true" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-navy-subtle shrink-0" aria-hidden="true" />
                )}
                <span className={check.met ? 'text-teal font-medium' : 'text-navy-subtle'}>
                  {check.label}
                </span>
              </div>
            ))}
          </div>

          <FormField label="Confirm New Password" htmlFor="conf-pass" required>
            <Input
              id="conf-pass"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </FormField>

          {confirmPassword && newPassword !== confirmPassword && (
            <p className="text-xs text-coral font-medium">Passwords do not match.</p>
          )}

          <div className="pt-2 flex justify-end gap-2">
            {!currentUser?.must_change_password && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setIsChangePasswordOpen(false)}
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={!isPasswordValid || newPassword !== confirmPassword}
              isLoading={changePasswordMutation.isPending}
            >
              Update Password
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Active Browser Sessions Dialog */}
      <Dialog
        isOpen={isManageSessionsOpen}
        onClose={() => setIsManageSessionsOpen(false)}
        title="Active Browser Sessions"
        maxWidth="lg"
        footer={<Button variant="primary" size="sm" onClick={() => setIsManageSessionsOpen(false)}>Done</Button>}
      >
        <div className="space-y-3 text-xs">
          <p className="text-navy-muted">
            All devices authenticated with your account. Revoking a session deletes its token digest immediately.
          </p>

          <div className="divide-y divide-border border border-border rounded-xl overflow-hidden">
            {activeSessions?.map((sess) => (
              <div key={sess.id} className="p-3.5 flex items-center justify-between gap-3 bg-white">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-navy">{sess.user_agent?.slice(0, 48) || 'Device'}</span>
                    {sess.is_current && <StatusBadge status="ACTIVE" label="Current" size="sm" />}
                  </div>
                  <div className="text-[11px] text-navy-subtle mt-0.5">
                    IP: {sess.ip_address || '127.0.0.1'} &bull; Created: {new Date(sess.created_at).toLocaleString()}
                  </div>
                </div>

                {!sess.is_current && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-coral hover:bg-coral-light/50"
                    onClick={() => revokeSessionMutation.mutate(sess.id)}
                    isLoading={revokeSessionMutation.isPending}
                  >
                    Revoke
                  </Button>
                )}
              </div>
            ))}
          </div>
        </div>
      </Dialog>

      {/* Phase 11 In-App Notification Centre & Communication Modal */}
      <NotificationCenterModal
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
        isSSEConnected={isSSEConnected}
        isSSEFallback={isSSEFallback}
      />
    </>
  );
};
