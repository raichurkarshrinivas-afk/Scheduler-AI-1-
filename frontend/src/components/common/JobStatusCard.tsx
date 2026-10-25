import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Clock,
  RotateCw,
  XCircle,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  Layers,
  StopCircle,
} from 'lucide-react';
import { BackgroundJob } from '../../types';
import { api } from '../../services/api';
import { Card } from './Card';
import { Button } from './Button';
import { StatusBadge } from './StatusBadge';
import { ConfirmationDialog } from './ConfirmationDialog';

export interface JobStatusCardProps {
  jobId: string;
  onClose?: () => void;
  onJobComplete?: (job: BackgroundJob) => void;
  className?: string;
}

export const JobStatusCard: React.FC<JobStatusCardProps> = ({
  jobId,
  onClose,
  onJobComplete,
  className = '',
}) => {
  const queryClient = useQueryClient();
  const [confirmCancelOpen, setConfirmCancelOpen] = useState(false);
  const [elapsedDisplay, setElapsedDisplay] = useState<string>('0s');

  // TanStack Query polling hook:
  // Polls every 1500ms while QUEUED or RUNNING; automatically stops when settled.
  const { data: job, isLoading, error } = useQuery<BackgroundJob>({
    queryKey: ['job', jobId],
    queryFn: () => api.jobs.getJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'QUEUED' || status === 'RUNNING' ? 1500 : false;
    },
  });

  // Calculate live elapsed duration without fake percentages
  useEffect(() => {
    if (!job) return;

    if (job.status === 'SUCCEEDED' || job.status === 'FAILED' || job.status === 'CANCELLED') {
      const sec = job.elapsed_seconds ?? 0;
      setElapsedDisplay(sec >= 60 ? `${Math.floor(sec / 60)}m ${Math.round(sec % 60)}s` : `${sec}s`);
      if (job.status === 'SUCCEEDED' && onJobComplete) {
        onJobComplete(job);
      }
      return;
    }

    const startTime = job.started_at ? new Date(job.started_at).getTime() : new Date(job.created_at).getTime();

    const updateTimer = () => {
      const now = Date.now();
      const diffSec = Math.max(0, Math.floor((now - startTime) / 1000));
      if (diffSec >= 60) {
        const mins = Math.floor(diffSec / 60);
        const secs = diffSec % 60;
        setElapsedDisplay(`${mins}m ${secs}s`);
      } else {
        setElapsedDisplay(`${diffSec}s`);
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [job, onJobComplete]);

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: () => api.jobs.cancelJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job', jobId] });
      setConfirmCancelOpen(false);
    },
  });

  if (isLoading) {
    return (
      <Card className={`p-4 ${className}`}>
        <div className="flex items-center gap-3">
          <RotateCw className="w-5 h-5 text-teal animate-spin" aria-hidden="true" />
          <div className="space-y-1">
            <span className="text-sm font-semibold text-navy">Connecting to Background Engine...</span>
            <p className="text-xs text-navy-muted">Querying job status lease...</p>
          </div>
        </div>
      </Card>
    );
  }

  if (error || !job) {
    return (
      <Card className={`p-4 border-coral/30 bg-coral-light/20 ${className}`}>
        <div className="flex items-center gap-3 text-coral">
          <AlertTriangle className="w-5 h-5 shrink-0" aria-hidden="true" />
          <div className="text-xs">
            <span className="font-semibold block">Failed to load job details</span>
            <span>{error instanceof Error ? error.message : 'Job not found or access denied.'}</span>
          </div>
        </div>
      </Card>
    );
  }

  const isTerminal =
    job.status === 'SUCCEEDED' || job.status === 'FAILED' || job.status === 'CANCELLED';

  const canCancel =
    (job.status === 'QUEUED' || job.status === 'RUNNING') && !job.cancellation_requested;

  return (
    <Card className={`bg-white border-2 border-border shadow-card ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 mb-3 border-b border-border">
        <div className="flex items-center gap-2.5">
          <Cpu className="w-5 h-5 text-teal shrink-0" aria-hidden="true" />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-heading font-bold text-sm text-navy">{job.job_type}</h3>
              <StatusBadge status={job.status} size="sm" />
            </div>
            <span className="text-[11px] text-navy-subtle">
              Job ID: <code className="bg-bg px-1 rounded font-mono">{job.id.slice(0, 8)}</code> &bull; Attempt {job.attempt_count} of {job.max_attempts}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {canCancel && (
            <Button
              variant="danger"
              size="sm"
              leftIcon={<StopCircle className="w-3.5 h-3.5" />}
              onClick={() => setConfirmCancelOpen(true)}
              isLoading={cancelMutation.isPending}
            >
              Cancel Job
            </Button>
          )}

          {isTerminal && onClose && (
            <Button variant="ghost" size="sm" onClick={onClose}>
              Dismiss
            </Button>
          )}
        </div>
      </div>

      {/* Body: Meaningful Phase Label and Elapsed Time (STRICTLY NO FAKE PERCENTAGES) */}
      <div className="space-y-3">
        <div className="p-3.5 rounded-lg bg-bg border border-border flex items-start justify-between gap-4">
          <div className="space-y-1">
            <span className="text-[11px] text-navy-subtle uppercase tracking-wider font-semibold block">
              Current Operating Phase
            </span>
            <div className="flex items-center gap-2">
              {!isTerminal && (
                <span className="w-2 h-2 rounded-full bg-teal animate-pulse" aria-hidden="true" />
              )}
              {job.status === 'SUCCEEDED' && (
                <CheckCircle2 className="w-4 h-4 text-teal" aria-hidden="true" />
              )}
              {job.status === 'FAILED' && (
                <XCircle className="w-4 h-4 text-coral" aria-hidden="true" />
              )}
              {job.status === 'CANCELLED' && (
                <AlertTriangle className="w-4 h-4 text-amber" aria-hidden="true" />
              )}
              <span className="font-semibold text-sm text-navy">{job.phase_label}</span>
            </div>
          </div>

          <div className="text-right shrink-0">
            <span className="text-[11px] text-navy-subtle uppercase tracking-wider font-semibold block">
              Elapsed Time
            </span>
            <span className="font-mono font-bold text-sm text-navy flex items-center gap-1 justify-end">
              <Clock className="w-3.5 h-3.5 text-navy-muted" aria-hidden="true" />
              {elapsedDisplay}
            </span>
          </div>
        </div>

        {/* Structured Results Display when Succeeded */}
        {job.status === 'SUCCEEDED' && job.result_reference && (
          <div className="p-3.5 rounded-lg bg-teal-light/40 border border-teal/30 text-xs space-y-2">
            <span className="font-heading font-semibold text-teal flex items-center gap-1.5">
              <Layers className="w-4 h-4" aria-hidden="true" />
              Engine Result Reference
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {Object.entries(job.result_reference).map(([k, v]) => (
                <div key={k} className="p-2 rounded bg-white/80 border border-teal/20">
                  <span className="text-[10px] text-navy-subtle uppercase block truncate">
                    {k.replace(/_/g, ' ')}
                  </span>
                  <span className="font-semibold text-navy text-xs truncate block">
                    {String(v)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Structured Failure Code Display when Failed */}
        {job.status === 'FAILED' && (
          <div className="p-3.5 rounded-lg bg-coral-light/40 border border-coral/30 text-xs space-y-1.5">
            <div className="flex items-center gap-1.5 text-coral font-bold">
              <XCircle className="w-4 h-4" aria-hidden="true" />
              <span>Failure Code: [{job.error_code || 'UNSPECIFIED_FAILURE'}]</span>
            </div>
            <p className="text-navy leading-relaxed pl-5">
              {job.error_message || 'An unrecoverable failure occurred during job execution.'}
            </p>
          </div>
        )}

        {/* Cancellation Notice */}
        {job.cancellation_requested && job.status !== 'CANCELLED' && (
          <div className="text-[11px] text-amber flex items-center gap-1.5 font-medium">
            <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
            Cancellation requested. Worker will abort at the next operational checkpoint.
          </div>
        )}
      </div>

      {/* Confirmation Dialog for Cancellation */}
      <ConfirmationDialog
        isOpen={confirmCancelOpen}
        title="Cancel Background Job"
        message={`Are you sure you want to stop background job ${job.job_type} (${job.id.slice(0, 8)})? In-flight constraint solving will be aborted immediately.`}
        confirmLabel="Confirm Cancellation"
        isDestructive={true}
        onConfirm={() => cancelMutation.mutate()}
        onClose={() => setConfirmCancelOpen(false)}
        isLoading={cancelMutation.isPending}
      />
    </Card>
  );
};
