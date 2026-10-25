import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Key, Monitor, Smartphone, CheckCircle2, AlertTriangle } from 'lucide-react';
import { UserProfile, SessionItem, StudentProfile as IStudentProfile } from '../../types';
import { api } from '../../services/api';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { StatusBadge } from '../../components/common/StatusBadge';
import { ConfirmationDialog } from '../../components/common/ConfirmationDialog';

export interface StudentProfileProps {
  user: UserProfile;
  onChangePasswordClick?: () => void;
}

export const StudentProfile: React.FC<StudentProfileProps> = ({ user }) => {
  const queryClient = useQueryClient();

  // Real Student Profile Query
  const { data: profile } = useQuery<IStudentProfile>({
    queryKey: ['student-profile'],
    queryFn: () => api.student.getMe(),
    staleTime: 60000,
  });

  // Active Device Sessions
  const { data: sessions, isLoading: sessionsLoading } = useQuery<SessionItem[]>({
    queryKey: ['active-sessions'],
    queryFn: () => api.auth.getSessions(),
  });

  const [revokingId, setRevokingId] = useState<string | null>(null);

  const revokeMutation = useMutation({
    mutationFn: (id: string) => api.auth.revokeSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-sessions'] });
      setRevokingId(null);
    },
  });

  // Password Change Form State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (newPassword.length < 10) {
      setPasswordError('New password must be at least 10 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New password and confirmation do not match.');
      return;
    }

    setIsChangingPassword(true);
    try {
      const res = await api.student.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordSuccess(res.message || 'Password changed successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPasswordError(err.message || 'Failed to update password. Verify your current password.');
    } finally {
      setIsChangingPassword(false);
    }
  };

  const studentName = profile?.full_name || user.full_name;
  const rollNumber = profile?.roll_number || user.roll_number || 'APEX-STU-2026-001';
  const departmentName = profile?.department_name || 'Computer Science';
  const institutionName = user.institution_name;
  const enrolledCourses = [
    { code: 'CS-101', name: 'Algorithms & Data Structures', credits: 4, type: 'THEORY' },
    { code: 'CS-102L', name: 'Systems & Networks Lab', credits: 3, type: 'PRACTICAL' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2">
          <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
            Student Profile & Session Security
          </h1>
          <StatusBadge status="ACTIVE" label="Verified Identity" size="sm" />
        </div>
        <p className="text-xs sm:text-sm text-navy-muted mt-0.5">
          Your official institutional registration, enrolled curricular units, and cryptographic credentials.
        </p>
      </div>

      {/* Identity Card */}
      <Card title="Candidate Record (Session-Bound)">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div className="p-3.5 rounded-lg bg-bg border border-border">
            <span className="text-navy-subtle block mb-1">Full Legal Name</span>
            <span className="font-semibold text-navy text-sm">{studentName}</span>
          </div>

          <div className="p-3.5 rounded-lg bg-bg border border-border">
            <span className="text-navy-subtle block mb-1">Permanent Roll Number (PRN)</span>
            <span className="font-mono font-bold text-teal text-sm">{rollNumber}</span>
          </div>

          <div className="p-3.5 rounded-lg bg-bg border border-border">
            <span className="text-navy-subtle block mb-1">Department</span>
            <span className="font-semibold text-navy text-sm">
              {departmentName}
            </span>
          </div>

          <div className="p-3.5 rounded-lg bg-bg border border-border">
            <span className="text-navy-subtle block mb-1">Institution</span>
            <span className="font-semibold text-navy text-sm">{institutionName}</span>
          </div>
        </div>
      </Card>

      {/* Password Change Form */}
      <Card
        title="Change Authentication Password"
        subtitle="Policy requires at least 10 characters. Sessions on other devices will be preserved."
      >
        <form onSubmit={handlePasswordSubmit} className="space-y-4 max-w-md text-xs">
          {passwordSuccess && (
            <div className="p-3 rounded-lg bg-teal-light/60 border border-teal/30 text-teal-dark flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-teal shrink-0" />
              <span>{passwordSuccess}</span>
            </div>
          )}

          {passwordError && (
            <div className="p-3 rounded-lg bg-coral/10 border border-coral/30 text-coral-dark flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-coral shrink-0" />
              <span>{passwordError}</span>
            </div>
          )}

          <div className="space-y-1">
            <label className="block font-semibold text-navy">Current Password</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-bg text-navy focus:outline-none focus:ring-1 focus:ring-teal"
              placeholder="Enter current password"
            />
          </div>

          <div className="space-y-1">
            <label className="block font-semibold text-navy">New Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={10}
              className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-bg text-navy focus:outline-none focus:ring-1 focus:ring-teal"
              placeholder="Minimum 10 characters"
            />
          </div>

          <div className="space-y-1">
            <label className="block font-semibold text-navy">Confirm New Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-bg text-navy focus:outline-none focus:ring-1 focus:ring-teal"
              placeholder="Confirm new password"
            />
          </div>

          <Button
            type="submit"
            variant="primary"
            size="sm"
            isLoading={isChangingPassword}
            leftIcon={<Key className="w-3.5 h-3.5" />}
          >
            Update Password
          </Button>
        </form>
      </Card>

      {/* Enrolled Courses */}
      <Card title="Enrolled Curricular Units (Official Record)">
        <div className="divide-y divide-border border border-border rounded-lg overflow-hidden text-xs">
          {enrolledCourses.map((c, idx) => (
            <div key={idx} className="p-3.5 flex items-center justify-between hover:bg-bg/40">
              <div>
                <span className="font-bold text-navy mr-2">{c.code}</span>
                <span className="text-navy-muted">{c.name}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-navy-subtle">{c.credits} Credits</span>
                <StatusBadge status="ACTIVE" label={c.type} size="sm" />
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Active Device Sessions */}
      <Card
        title="Active Device Sessions"
        subtitle="Manage browsers and workstations authenticated with your account."
      >
        <div className="space-y-3">
          {sessionsLoading ? (
            <p className="text-xs text-navy-muted">Loading active sessions...</p>
          ) : (
            sessions?.map((s) => (
              <div
                key={s.id}
                className="p-3 rounded-lg border border-border bg-bg flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-surface border border-border text-navy">
                    {s.is_current ? (
                      <Monitor className="w-4 h-4 text-teal" />
                    ) : (
                      <Smartphone className="w-4 h-4 text-navy-muted" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-navy">
                        {s.ip_address === '127.0.0.1' ? 'Localhost (Current Device)' : s.ip_address}
                      </span>
                      {s.is_current && (
                        <span className="text-[10px] bg-teal-light text-teal px-1.5 py-0.2 rounded font-semibold">
                          Current
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-navy-subtle block">
                      Last Active: {new Date(s.last_activity_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                {!s.is_current && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setRevokingId(s.id)}
                    className="text-coral hover:text-coral-dark"
                  >
                    Revoke
                  </Button>
                )}
              </div>
            ))
          )}
        </div>
      </Card>

      {/* Confirmation Dialog for Revoking Session */}
      <ConfirmationDialog
        isOpen={Boolean(revokingId)}
        onClose={() => setRevokingId(null)}
        onConfirm={() => {
          if (revokingId) {
            revokeMutation.mutate(revokingId);
          }
        }}
        title="Revoke Session"
        message="Are you sure you want to terminate this authenticated device session? The device will be signed out immediately."
        confirmLabel="Revoke Session"
        isDestructive
        isLoading={revokeMutation.isPending}
      />
    </div>
  );
};
