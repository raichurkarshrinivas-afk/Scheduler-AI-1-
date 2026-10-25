import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Monitor, ShieldCheck, Smartphone, Copy, Check, Sparkles, FileSpreadsheet } from 'lucide-react';
import { UserProfile, SessionItem, AIStatusOut } from '../../types';
import { api } from '../../services/api';
import { Card } from '../../components/common/Card';
import { FormField, Input } from '../../components/common/FormField';
import { Button } from '../../components/common/Button';
import { StatusBadge } from '../../components/common/StatusBadge';
import { ConfirmationDialog } from '../../components/common/ConfirmationDialog';
import { AIColumnMappingModal } from '../../components/common/AIColumnMappingModal';

export interface StaffSettingsProps {
  user: UserProfile;
}

export const StaffSettings: React.FC<StaffSettingsProps> = ({ user }) => {
  const queryClient = useQueryClient();
  const isAdmin = user.role === 'INSTITUTION_ADMINISTRATOR';

  // Admin Reset State
  const [resetUserId, setResetUserId] = useState('');
  const [resetResult, setResetResult] = useState<{
    temporary_password: string;
    user_id: string;
  } | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Active Sessions
  const { data: sessions, isLoading: sessionsLoading } = useQuery<SessionItem[]>({
    queryKey: ['active-sessions'],
    queryFn: () => api.auth.getSessions(),
  });

  const [revokingId, setRevokingId] = useState<string | null>(null);

  // Phase 13 AI Assistant Status
  const [isColumnMappingOpen, setIsColumnMappingOpen] = useState(false);
  const { data: aiStatus } = useQuery<AIStatusOut>({
    queryKey: ['ai-status'],
    queryFn: () => api.ai.getStatus(),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => api.auth.revokeSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-sessions'] });
      setRevokingId(null);
    },
  });

  const adminResetMutation = useMutation({
    mutationFn: (userId: string) => api.auth.adminResetPassword(userId, {}),
    onSuccess: (data) => {
      setResetResult(data);
      setResetError(null);
    },
    onError: (err: any) => {
      setResetError(err.message || 'Failed to execute administrative password reset');
      setResetResult(null);
    },
  });

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
          Institutional Settings & Security Controls
        </h1>
        <p className="text-xs sm:text-sm text-navy-muted">
          Manage institution configuration, administrator member resets, and active sessions.
        </p>
      </div>

      {/* Institution Parameters */}
      <Card title="Institution Profile">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="p-3 rounded-lg bg-bg border border-border">
            <span className="text-navy-subtle block">Institution Name</span>
            <span className="font-semibold text-navy text-sm">{user.institution_name}</span>
          </div>
          <div className="p-3 rounded-lg bg-bg border border-border">
            <span className="text-navy-subtle block">Tenant Code</span>
            <span className="font-semibold text-teal text-sm">{user.institution_code}</span>
          </div>
          <div className="p-3 rounded-lg bg-bg border border-border">
            <span className="text-navy-subtle block">Default Timezone</span>
            <span className="font-semibold text-navy text-sm">Asia/Kolkata (UTC+05:30)</span>
          </div>
        </div>
      </Card>

      {/* Admin Reset Password Workflow (Admin Only) */}
      {isAdmin && (
        <Card title="Administrative Credential Reset Workflow">
          <p className="text-xs text-navy-muted mb-4">
            Reset credentials for teachers or students within {user.institution_code}. Generates a secure temporary password and flags <code className="bg-bg px-1 py-0.5 rounded text-[11px]">must_change_password = true</code>.
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (resetUserId.trim()) {
                adminResetMutation.mutate(resetUserId.trim());
              }
            }}
            className="space-y-4 max-w-md"
          >
            <FormField label="Target User UUID" htmlFor="reset-user-id" required>
              <Input
                id="reset-user-id"
                placeholder="e.g. paste target user UUID"
                value={resetUserId}
                onChange={(e) => setResetUserId(e.target.value)}
                required
              />
            </FormField>

            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={adminResetMutation.isPending}
            >
              Issue Temporary Password
            </Button>
          </form>

          {resetError && (
            <div className="mt-4 p-3 rounded-lg bg-coral-light border border-coral/30 text-xs text-coral" role="alert">
              {resetError}
            </div>
          )}

          {resetResult && (
            <div className="mt-4 p-4 rounded-xl bg-teal-light border border-teal/30 space-y-2 text-xs">
              <div className="font-semibold text-navy flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-teal" aria-hidden="true" />
                Temporary Credentials Generated
              </div>
              <p className="text-navy-muted">
                Provide these credentials securely to the user. First login will enforce a password change.
              </p>
              <div className="flex items-center gap-2 pt-1">
                <code className="p-2 rounded bg-white border border-teal/40 font-mono text-sm font-bold text-teal">
                  {resetResult.temporary_password}
                </code>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleCopy(resetResult.temporary_password)}
                  leftIcon={copied ? <Check className="w-3.5 h-3.5 text-teal" /> : <Copy className="w-3.5 h-3.5" />}
                >
                  {copied ? 'Copied' : 'Copy'}
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Phase 13: AI Assistant Configuration & Cost Visibility */}
      <Card
        title="AI-Assisted Interpretation & Diagnostic Engine"
        subtitle="Operational status, provider mode, cost accounting, and tabular schema tools."
      >
        <div className="space-y-4 text-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-surface border border-border rounded-xl">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-teal-light flex items-center justify-center text-teal shrink-0 mt-0.5">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-navy text-sm">
                    Provider Mode: {aiStatus?.provider?.toUpperCase() || 'MOCK'}
                  </span>
                  <StatusBadge
                    status={aiStatus?.is_available ? 'ACTIVE' : 'PENDING'}
                    label={aiStatus?.is_available ? 'AVAILABLE' : 'DISABLED'}
                    size="sm"
                  />
                </div>
                <p className="text-[11px] text-navy-muted mt-0.5">
                  Model: <span className="font-mono">{aiStatus?.model_name || 'mock-deterministic-v1'}</span> &bull; Air-gap compliant &bull; No SQL or tool execution authority.
                </p>
              </div>
            </div>

            <Button
              variant="secondary"
              size="sm"
              leftIcon={<FileSpreadsheet className="w-3.5 h-3.5" />}
              onClick={() => setIsColumnMappingOpen(true)}
              className="text-xs shrink-0"
              id="test-column-mapping-btn"
            >
              Test Column Mapping
            </Button>
          </div>

          {/* Usage Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 bg-bg border border-border rounded-lg">
              <span className="text-[10px] text-navy-subtle uppercase font-semibold block">Total Requests</span>
              <span className="text-base font-bold text-navy">{aiStatus?.total_requests ?? 0}</span>
            </div>
            <div className="p-3 bg-bg border border-border rounded-lg">
              <span className="text-[10px] text-navy-subtle uppercase font-semibold block">Processed Tokens</span>
              <span className="text-base font-bold text-navy">{aiStatus?.total_tokens ?? 0}</span>
            </div>
            <div className="p-3 bg-bg border border-border rounded-lg">
              <span className="text-[10px] text-navy-subtle uppercase font-semibold block">Estimated API Cost</span>
              <span className="text-base font-bold text-teal">${aiStatus?.estimated_cost_usd?.toFixed(4) ?? '0.0000'}</span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-teal-light/40 border border-teal/20 text-[11px] text-navy-muted leading-relaxed">
            <strong>Advisory Integrity Guarantee:</strong> {aiStatus?.disclaimer || 'AI suggestions are unverified candidate interpretations. You must review and validate against institutional rules before applying.'}
          </div>
        </div>
      </Card>

      {/* Active Browser Sessions Inspector */}
      <Card title="Active Browser Sessions">
        <p className="text-xs text-navy-muted mb-4">
          All devices currently authenticated with your account. Revoking a session immediately deletes its server-side token digest.
        </p>

        {sessionsLoading ? (
          <div className="py-6 text-center text-xs text-navy-subtle">Loading active sessions...</div>
        ) : (
          <div className="divide-y divide-border border border-border rounded-lg overflow-hidden text-xs">
            {sessions?.map((sess) => (
              <div key={sess.id} className="p-3.5 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-bg border border-border text-navy-muted">
                    {sess.user_agent?.toLowerCase().includes('mobile') ? (
                      <Smartphone className="w-4 h-4" />
                    ) : (
                      <Monitor className="w-4 h-4" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-navy">
                        {sess.user_agent?.slice(0, 48) || 'Browser Session'}
                      </span>
                      {sess.is_current && (
                        <StatusBadge status="ACTIVE" label="Current Session" size="sm" />
                      )}
                    </div>
                    <div className="text-navy-subtle text-[11px] mt-0.5">
                      IP: {sess.ip_address || '127.0.0.1'} &bull; Created: {new Date(sess.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                {!sess.is_current && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-coral hover:bg-coral-light/50"
                    onClick={() => setRevokingId(sess.id)}
                  >
                    Revoke
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Phase 13 AI Column Mapping Modal */}
      <AIColumnMappingModal
        isOpen={isColumnMappingOpen}
        onClose={() => setIsColumnMappingOpen(false)}
      />

      {/* Confirmation Dialog for Revocation */}
      <ConfirmationDialog
        isOpen={Boolean(revokingId)}
        onClose={() => setRevokingId(null)}
        onConfirm={() => {
          if (revokingId) revokeMutation.mutate(revokingId);
        }}
        title="Revoke Session"
        message="Are you sure you want to sign out this device? The user will be required to authenticate again."
        confirmLabel="Revoke Session"
        isDestructive
        isLoading={revokeMutation.isPending}
      />
    </div>
  );
};
