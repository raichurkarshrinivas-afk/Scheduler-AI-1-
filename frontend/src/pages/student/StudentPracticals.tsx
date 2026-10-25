import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Monitor, Cpu, HardDrive, User, Clock, AlertCircle } from 'lucide-react';
import { Card } from '../../components/common/Card';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Button } from '../../components/common/Button';
import { api } from '../../services/api';
import { StudentPractical } from '../../types';

export const StudentPracticals: React.FC = () => {
  const {
    data: practicals,
    isLoading,
    error,
    refetch,
  } = useQuery<StudentPractical[]>({
    queryKey: ['student-practicals'],
    queryFn: () => api.student.getPracticals(),
    staleTime: 60000,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
          Practical Examinations & Lab Workstations
        </h1>
        <p className="text-xs sm:text-sm text-navy-muted">
          Your assigned hardware terminals, operating systems, and practical exam rotations.
        </p>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="py-20 text-center space-y-3">
          <div className="w-8 h-8 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-navy-muted">
            Loading allocated practical workstations & lab configurations...
          </p>
        </div>
      ) : error ? (
        <div className="p-6 rounded-xl bg-surface border border-border text-center space-y-2">
          <AlertCircle className="w-8 h-8 text-coral mx-auto" />
          <h3 className="font-heading font-bold text-navy text-sm">Failed to Load Workstations</h3>
          <p className="text-xs text-navy-muted">{(error as any)?.message || 'An error occurred.'}</p>
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      ) : !practicals || practicals.length === 0 ? (
        <Card className="text-center py-12 space-y-2">
          <Monitor className="w-8 h-8 text-navy-subtle mx-auto" />
          <h3 className="font-heading font-bold text-navy text-base">
            No Practical Workstations Assigned
          </h3>
          <p className="text-xs text-navy-muted max-w-sm mx-auto">
            Practical laboratory examination rotations have not yet been published for your enrolled
            units.
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          {practicals.map((p, idx) => (
            <Card
              key={idx}
              title={p.exam_name}
              action={<StatusBadge status="ACTIVE" label="Assigned & Ready" />}
            >
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-1.5 font-medium text-navy">
                    <Clock className="w-3.5 h-3.5 text-teal" />
                    <span>
                      Batch: {p.batch_name} &bull; Start: {p.start_time} ({p.duration_minutes} min)
                    </span>
                  </div>
                  <span className="text-navy-subtle flex items-center gap-1">
                    <User className="w-3 h-3 text-teal" /> Examiner: {p.examiner_name || 'Department Faculty'}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-bg border border-border grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                  <div>
                    <span className="text-navy-subtle block mb-1">Terminal Desk</span>
                    <span className="font-heading font-bold text-base text-teal">
                      {p.station_code}
                    </span>
                    <span className="text-[11px] text-navy-muted block">{p.lab_name}</span>
                  </div>

                  <div>
                    <span className="text-navy-subtle block mb-1">Operating System</span>
                    <span className="font-semibold text-navy flex items-center gap-1">
                      <Monitor className="w-3.5 h-3.5 text-teal" /> {p.os || 'Linux Sandbox'}
                    </span>
                  </div>

                  <div>
                    <span className="text-navy-subtle block mb-1">Hardware / Features</span>
                    <span className="font-semibold text-navy flex items-center gap-1">
                      <Cpu className="w-3.5 h-3.5 text-teal" /> {p.installed_features?.join(', ') || 'Standard Lab Tools'}
                    </span>
                  </div>

                  <div>
                    <span className="text-navy-subtle block mb-1">Environment Access</span>
                    <span className="font-semibold text-teal flex items-center gap-1">
                      <HardDrive className="w-3.5 h-3.5" /> Isolated Sandbox
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
