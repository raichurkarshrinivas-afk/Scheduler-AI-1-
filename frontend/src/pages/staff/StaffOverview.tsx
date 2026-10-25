import React from 'react';
import {
  Calendar,
  Layers,
  Building2,
  ShieldCheck,
  ArrowRight,
  Clock,
} from 'lucide-react';
import { UserProfile } from '../../types';
import { MetricCard } from '../../components/common/Card';
import { Card } from '../../components/common/Card';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Button } from '../../components/common/Button';

export interface StaffOverviewProps {
  user: UserProfile;
  onNavigate: (path: string) => void;
}

export const StaffOverview: React.FC<StaffOverviewProps> = ({ user, onNavigate }) => {
  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl bg-surface border border-border shadow-subtle">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
              Welcome back, {user.full_name}
            </h1>
            <StatusBadge status="ACTIVE" label={user.role.replace('_', ' ')} size="sm" />
          </div>
          <p className="text-xs sm:text-sm text-navy-muted">
            Institutional Context: <strong>{user.institution_name} ({user.institution_code})</strong> &bull; Term: Autumn 2026
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="primary"
            size="sm"
            onClick={() => onNavigate('timetables')}
            rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
          >
            Open Timetables
          </Button>
        </div>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Active Term"
          value="Autumn 2026"
          icon={<Calendar className="w-4 h-4 text-teal" />}
          change="In Session"
          trend="up"
        />
        <MetricCard
          label="Course Offerings"
          value="48"
          icon={<Layers className="w-4 h-4 text-ice" />}
          change="Verified"
          trend="neutral"
        />
        <MetricCard
          label="Exam Benches"
          value="180"
          icon={<Building2 className="w-4 h-4 text-amber-700" />}
          change="Single-Desk"
          trend="up"
        />
        <MetricCard
          label="Security Audits"
          value="24"
          icon={<ShieldCheck className="w-4 h-4 text-teal" />}
          change="Logged"
          trend="neutral"
        />
      </div>

      {/* Module Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card
          title="Class Timetables"
          subtitle="Academic Weekly Matrices"
          action={<StatusBadge status="PUBLISHED" label="Published" size="sm" />}
          hoverable
          onClick={() => onNavigate('timetables')}
        >
          <p className="text-xs text-navy-muted mb-4">
            Curricular schedule with lecture, tutorial, and practical session mappings. 0 room or faculty conflicts.
          </p>
          <div className="text-xs font-semibold text-teal flex items-center gap-1">
            <span>Inspect Schedule</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </Card>

        <Card
          title="Examination Sittings"
          subtitle="Practical & Theory Exams"
          action={<StatusBadge status="CHECKED" label="Checking" size="sm" />}
          hoverable
          onClick={() => onNavigate('examinations')}
        >
          <p className="text-xs text-navy-muted mb-4">
            Anti-cheating exam seating allocations and laboratory practical workstation batching.
          </p>
          <div className="text-xs font-semibold text-teal flex items-center gap-1">
            <span>Manage Examinations</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </Card>

        <Card
          title="Campus Facilities"
          subtitle="Rooms & Workstations"
          action={<StatusBadge status="ACTIVE" label="Ready" size="sm" />}
          hoverable
          onClick={() => onNavigate('resources')}
        >
          <p className="text-xs text-navy-muted mb-4">
            Rooms with explicit physical capacity vs usable exam benches, plus lab GPU terminals.
          </p>
          <div className="text-xs font-semibold text-teal flex items-center gap-1">
            <span>View Infrastructure</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </Card>
      </div>

      {/* Security Status Card */}
      <Card title="Institutional Security & Integrity Log">
        <div className="space-y-3 text-xs">
          <div className="flex items-center justify-between p-3 rounded-lg bg-bg border border-border">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="w-4 h-4 text-teal" aria-hidden="true" />
              <div>
                <div className="font-semibold text-navy">Tenant Isolation Verified</div>
                <div className="text-navy-subtle text-[11px]">Composite foreign key integrity active for {user.institution_code}</div>
              </div>
            </div>
            <StatusBadge status="ACTIVE" label="Enforced" size="sm" />
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg bg-bg border border-border">
            <div className="flex items-center gap-2.5">
              <Clock className="w-4 h-4 text-ice" aria-hidden="true" />
              <div>
                <div className="font-semibold text-navy">Current Active Session</div>
                <div className="text-navy-subtle text-[11px]">Server-side HttpOnly cookie with SHA-256 token digest</div>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={() => onNavigate('settings')}>
              Manage Sessions
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};
