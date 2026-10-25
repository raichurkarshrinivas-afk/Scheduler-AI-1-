import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BookOpen,
  MapPin,
  Monitor,
  Ticket,
  ArrowRight,
  Clock,
  Calendar,
  AlertCircle,
  Bell,
  CheckCircle2,
} from 'lucide-react';
import { UserProfile, StudentHomeData } from '../../types';
import { Card, MetricCard } from '../../components/common/Card';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Button } from '../../components/common/Button';
import { api } from '../../services/api';

export interface StudentHomeProps {
  user: UserProfile;
  onNavigate: (path: string) => void;
}

export const StudentHome: React.FC<StudentHomeProps> = ({ user, onNavigate }) => {
  const {
    data: homeData,
    isLoading,
    error,
    refetch,
  } = useQuery<StudentHomeData>({
    queryKey: ['student-home'],
    queryFn: () => api.student.getHome(),
    staleTime: 30000,
  });

  if (isLoading) {
    return (
      <div className="py-20 text-center space-y-3">
        <div className="w-8 h-8 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-xs text-navy-muted">
          Loading your official published schedule & allocations...
        </p>
      </div>
    );
  }

  if (error || !homeData) {
    return (
      <div className="p-6 rounded-xl bg-surface border border-border shadow-subtle text-center space-y-3">
        <AlertCircle className="w-8 h-8 text-coral mx-auto" />
        <h3 className="font-heading font-bold text-navy text-base">Unable to Load Schedule</h3>
        <p className="text-xs text-navy-muted max-w-md mx-auto">
          {(error as any)?.message ||
            'Could not retrieve official schedule. Ensure your student session is active.'}
        </p>
        <Button variant="secondary" size="sm" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  const studentName = homeData.profile?.full_name || user.full_name;
  const rollNumber = homeData.profile?.roll_number || user.roll_number || 'APEX-STU-2026-001';
  const departmentName = homeData.profile?.department_name || 'Computer Science';
  const nextUp = homeData.next_up;
  const todaySchedule = homeData.today_schedule || [];
  const upcomingExams = homeData.upcoming_exams || [];
  const practicalSessions = homeData.practical_sessions || [];
  const recentChanges = homeData.recent_changes || [];
  const activePractical = practicalSessions[0] || null;

  return (
    <div className="space-y-6">
      {/* Student Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl bg-surface border border-border shadow-subtle">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
              Welcome, {studentName}
            </h1>
            <StatusBadge status="ACTIVE" label="Enrolled Student" size="sm" />
          </div>
          <p className="text-xs sm:text-sm text-navy-muted">
            PRN: <strong className="font-mono text-teal">{rollNumber}</strong> &bull; Dept: {departmentName}
          </p>
          <div className="flex items-center gap-2 mt-1 text-[11px] text-navy-subtle">
            <span>Status: Official Published Release</span>
            {homeData.publication_version && (
              <>
                <span>&bull;</span>
                <span className="font-mono text-teal font-semibold">v{homeData.publication_version}</span>
              </>
            )}
          </div>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={() => onNavigate('timetable')}
          rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
        >
          View Full Timetable
        </Button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricCard
          label="Today's Classes"
          value={todaySchedule.length.toString()}
          icon={<Clock className="w-4 h-4 text-teal" />}
          change={todaySchedule.length > 0 ? 'In Session' : 'No Classes Today'}
          trend="neutral"
        />
        <MetricCard
          label="Next-Up Class"
          value={nextUp ? nextUp.subject_code : 'None'}
          icon={<BookOpen className="w-4 h-4 text-ice" />}
          change={nextUp ? `${nextUp.start_time} - ${nextUp.room_name}` : 'Completed'}
          trend="up"
        />
        <MetricCard
          label="Practical Workstation"
          value={activePractical ? activePractical.station_code : 'Pending'}
          icon={<Monitor className="w-4 h-4 text-amber-700" />}
          change={activePractical ? activePractical.lab_name : 'No Lab Scheduled'}
          trend="neutral"
        />
        <MetricCard
          label="Upcoming Exams"
          value={upcomingExams.length > 0 ? upcomingExams[0].bench_label : 'None'}
          icon={<Ticket className="w-4 h-4 text-teal" />}
          change={
            upcomingExams.length > 0
              ? upcomingExams[0].hall_name
              : 'None Scheduled'
          }
          trend="up"
        />
      </div>

      {/* Next Class & Assigned Lab Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Next Class Card */}
        <Card
          title="Next Scheduled Class"
          subtitle={nextUp ? `Date: ${nextUp.date}` : 'Real-time schedule'}
          action={<StatusBadge status="PUBLISHED" label="Official Published" size="sm" />}
        >
          {nextUp ? (
            <div className="space-y-3">
              <div>
                <h3 className="font-heading font-semibold text-lg text-navy">
                  {nextUp.subject_name || nextUp.title}
                </h3>
                <p className="text-xs text-navy-muted">
                  Course <strong>{nextUp.subject_code}</strong>
                </p>
              </div>

              <div className="p-3 rounded-lg bg-bg border border-border flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 font-medium text-navy">
                  <MapPin className="w-4 h-4 text-teal" aria-hidden="true" />
                  {nextUp.room_name}
                </span>
                <span className="font-semibold text-teal font-mono">
                  {nextUp.start_time} - {nextUp.end_time}
                </span>
              </div>

              <div className="text-xs text-navy-subtle flex justify-between">
                <span>Instructor: {nextUp.teacher_name}</span>
                <span>Section: {nextUp.section_name || 'Enrolled Section'}</span>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-navy-muted space-y-1">
              <Calendar className="w-6 h-6 text-navy-subtle mx-auto mb-1" />
              <p className="font-medium text-navy">No Upcoming Class Today</p>
              <p className="text-navy-subtle text-[11px]">
                Check your weekly timetable for subsequent days.
              </p>
            </div>
          )}
        </Card>

        {/* Allocated Practical Workstation */}
        <Card
          title="Allocated Practical Workstation"
          subtitle="Laboratory Examination & Practical Sittings"
          action={
            <StatusBadge
              status={activePractical ? 'ACTIVE' : 'DRAFT'}
              label={activePractical ? 'Assigned' : 'Pending'}
              size="sm"
            />
          }
        >
          {activePractical ? (
            <div className="space-y-3">
              <div>
                <h3 className="font-heading font-semibold text-lg text-navy">
                  {activePractical.exam_name}
                </h3>
                <p className="text-xs text-navy-muted">
                  Batch: {activePractical.batch_name} &bull; Start: {activePractical.start_time}
                </p>
              </div>

              <div className="p-3 rounded-lg bg-teal-light/50 border border-teal/20 flex items-center justify-between text-xs">
                <span className="font-bold text-navy flex items-center gap-1.5">
                  <Monitor className="w-4 h-4 text-teal" aria-hidden="true" />
                  {activePractical.lab_name} &bull; Workstation #{activePractical.station_code}
                </span>
                <span className="text-teal font-semibold">{activePractical.os || 'Linux Sandbox'}</span>
              </div>

              <div className="text-xs text-navy-subtle flex justify-between">
                <span>Features: {activePractical.installed_features?.join(', ') || 'Standard Lab Tools'}</span>
                <span>Examiner: {activePractical.examiner_name || 'Department Faculty'}</span>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-navy-muted space-y-1">
              <Monitor className="w-6 h-6 text-navy-subtle mx-auto mb-1" />
              <p className="font-medium text-navy">No Practical Workstations Assigned</p>
              <p className="text-navy-subtle text-[11px]">
                Laboratory sittings will appear here once official allocations are released.
              </p>
            </div>
          )}
        </Card>
      </div>

      {/* Upcoming Exams & Recent Changes Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Upcoming Exams Card */}
        <Card
          title="Theory Examination Seat Allocations"
          subtitle="Anti-cheating orthogonal spacing verified"
          action={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate('exams-seats')}
              rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
            >
              All Exam Slips
            </Button>
          }
        >
          {upcomingExams.length > 0 ? (
            <div className="space-y-3">
              {upcomingExams.slice(0, 2).map((exam, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-bg border border-border space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-bold text-navy text-sm block">
                        {exam.paper_name || exam.paper_code}
                      </span>
                      <span className="text-navy-muted text-[11px]">{exam.exam_name}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] text-navy-subtle block">Allocated Seat</span>
                      <span className="font-heading font-bold text-base text-teal">
                        {exam.bench_label}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-navy-subtle pt-1 border-t border-border">
                    <span className="flex items-center gap-1 font-medium text-navy">
                      <MapPin className="w-3.5 h-3.5 text-teal" />
                      {exam.hall_name}
                    </span>
                    <span>
                      Duration: {exam.duration_minutes} min
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-navy-muted space-y-1">
              <Ticket className="w-6 h-6 text-navy-subtle mx-auto mb-1" />
              <p className="font-medium text-navy">No Exam Sittings Published</p>
              <p className="text-navy-subtle text-[11px]">
                Theory seating hall tickets will appear here once official seating is released.
              </p>
            </div>
          )}
        </Card>

        {/* Recent Official Publication Notices */}
        <Card
          title="Recent Official Publication Notices"
          subtitle="Immutable audit log updates and timetable changes"
          action={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onNavigate('notifications')}
              rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
            >
              Notice Board
            </Button>
          }
        >
          {recentChanges.length > 0 ? (
            <div className="space-y-2.5">
              {recentChanges.slice(0, 3).map((change) => (
                <div
                  key={change.id}
                  className="p-3 rounded-xl bg-surface border border-border space-y-1 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <Bell className="w-3.5 h-3.5 text-teal shrink-0" />
                      <span className="font-semibold text-navy text-xs">{change.event_type}</span>
                    </div>
                    <span className="text-[10px] text-teal font-mono font-bold bg-teal-light px-1.5 py-0.5 rounded">
                      v{change.version_number}
                    </span>
                  </div>

                  <p className="text-navy-muted text-[11px] pl-5 leading-relaxed">
                    {change.note || 'Official schedule update released to student portal.'}
                  </p>

                  <div className="flex items-center justify-between text-[10px] text-navy-subtle pl-5 pt-1">
                    <span>{new Date(change.published_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-navy-muted space-y-1">
              <CheckCircle2 className="w-6 h-6 text-teal mx-auto mb-1" />
              <p className="font-medium text-navy">Zero Schedule Modifications</p>
              <p className="text-navy-subtle text-[11px]">
                You are currently viewing the latest published release.
              </p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
