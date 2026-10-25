import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Send,
  RotateCcw,
  RefreshCw,
} from 'lucide-react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { Table } from '../common/Table';
import { StatusBadge } from '../common/StatusBadge';
import { api } from '../../services/api';
import { OutboxEvent } from '../../types';

export const StaffOutboxSection: React.FC = () => {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const {
    data: outboxEvents,
    isLoading,
    refetch,
  } = useQuery<OutboxEvent[]>({
    queryKey: ['staff-outbox', statusFilter],
    queryFn: () => api.communication.getOutbox(statusFilter === 'ALL' ? undefined : statusFilter),
    staleTime: 15000,
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => api.communication.retryOutbox(id),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['staff-outbox'] });
    },
  });

  const total = outboxEvents?.length || 0;
  const dispatched = outboxEvents?.filter((e) => e.status === 'DISPATCHED').length || 0;
  const pending = outboxEvents?.filter((e) => e.status === 'PENDING').length || 0;
  const failed = outboxEvents?.filter((e) => e.status === 'FAILED').length || 0;

  const columns = [
    {
      key: 'event_role',
      header: 'Event & Role',
      accessor: (e: OutboxEvent) => (
        <div>
          <span className="font-semibold text-navy block">{e.event_type}</span>
          <span className="text-[10px] text-navy-subtle font-mono">
            ID: {e.id.slice(0, 8)} &bull; Target: {e.recipient_role}
          </span>
        </div>
      ),
    },
    {
      key: 'publication',
      header: 'Publication / Note',
      accessor: (e: OutboxEvent) => (
        <div className="max-w-[200px]">
          {e.publication_id ? (
            <span className="font-mono text-[11px] text-teal block truncate">
              Pub: {e.publication_id.slice(0, 8)}
            </span>
          ) : (
            <span className="text-[11px] text-navy-subtle block">System Alert</span>
          )}
          <span className="text-[11px] text-navy-muted truncate block">
            {e.payload?.publication_note || e.payload?.message || 'Standard publication'}
          </span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Delivery Status',
      accessor: (e: OutboxEvent) => (
        <div className="space-y-0.5">
          <StatusBadge
            status={
              e.status === 'DISPATCHED'
                ? 'ACTIVE'
                : e.status === 'FAILED'
                ? 'FAILED'
                : 'DRAFT'
            }
            label={e.status}
            size="sm"
          />
          {e.retry_count > 0 && (
            <span className="text-[10px] text-navy-subtle block">
              Retries: {e.retry_count}/{e.max_retries}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'error',
      header: 'Error / Next Attempt',
      accessor: (e: OutboxEvent) => (
        <div className="max-w-[180px] text-[11px]">
          {e.last_error ? (
            <span className="text-coral block truncate" title={e.last_error}>
              {e.last_error}
            </span>
          ) : e.status === 'DISPATCHED' ? (
            <span className="text-teal font-medium">Delivered Idempotently</span>
          ) : (
            <span className="text-navy-subtle">Awaiting processor</span>
          )}
          {e.next_retry_at && (
            <span className="text-[10px] text-navy-subtle block">
              Next: {new Date(e.next_retry_at).toLocaleTimeString()}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'created',
      header: 'Created',
      accessor: (e: OutboxEvent) => (
        <span className="text-[11px] text-navy-subtle">
          {new Date(e.created_at).toLocaleString([], {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      ),
    },
    {
      key: 'action',
      header: 'Action',
      accessor: (e: OutboxEvent) => (
        <Button
          variant="secondary"
          size="sm"
          className="text-[11px] h-7 px-2"
          onClick={() => retryMutation.mutate(e.id)}
          isLoading={retryMutation.isPending && retryMutation.variables === e.id}
          disabled={e.status === 'DISPATCHED'}
        >
          <RotateCcw className="w-3 h-3 mr-1" />
          Retry
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="p-3.5 bg-white">
          <span className="text-xs text-navy-muted block">Total Outbox Events</span>
          <span className="font-heading font-bold text-xl text-navy mt-1 block">{total}</span>
        </Card>
        <Card className="p-3.5 bg-white border-teal/30">
          <span className="text-xs text-teal font-medium block">Dispatched (Idempotent)</span>
          <span className="font-heading font-bold text-xl text-teal mt-1 block">{dispatched}</span>
        </Card>
        <Card className="p-3.5 bg-white border-amber/30">
          <span className="text-xs text-amber-800 font-medium block">Pending Processing</span>
          <span className="font-heading font-bold text-xl text-amber-800 mt-1 block">{pending}</span>
        </Card>
        <Card className="p-3.5 bg-white border-coral/30">
          <span className="text-xs text-coral font-medium block">Delivery Failures</span>
          <span className="font-heading font-bold text-xl text-coral mt-1 block">{failed}</span>
        </Card>
      </div>

      {/* Table Section */}
      <Card className="bg-white p-4 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="font-heading font-bold text-sm text-navy flex items-center gap-2">
              <Send className="w-4 h-4 text-teal" />
              Durable Outbox Queue & Retry Visibility
            </h3>
            <p className="text-xs text-navy-muted mt-0.5">
              Authorised staff delivery control. All retries are idempotent and never produce duplicate events or student notifications.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-lg border border-border bg-white text-navy font-medium"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending Only</option>
              <option value="DISPATCHED">Dispatched Only</option>
              <option value="FAILED">Failed Only</option>
            </select>

            <Button variant="secondary" size="sm" onClick={() => refetch()} isLoading={isLoading}>
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {isLoading ? (
          <div className="py-12 text-center text-xs text-navy-muted">
            <div className="w-6 h-6 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            Loading outbox items...
          </div>
        ) : (
          <Table
            data={outboxEvents || []}
            columns={columns}
            keyExtractor={(e) => e.id}
            emptyMessage="No communication outbox events found matching the filter."
          />
        )}
      </Card>
    </div>
  );
};
