import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Clock,
  MapPin,
  Calendar,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Lock,
  Globe,
} from 'lucide-react';
import { Card } from '../../components/common/Card';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Button } from '../../components/common/Button';
import { api } from '../../services/api';
import { StudentTimetableResponse, DatedOccurrence } from '../../types';

export const StudentTimetable: React.FC = () => {
  // Current week Monday ISO string calculation
  const getMondayOfCurrentWeek = () => {
    const today = new Date();
    const day = today.getDay();
    const diff = today.getDate() - day + (day === 0 ? -6 : 1);
    const monday = new Date(today.setDate(diff));
    return monday.toISOString().split('T')[0];
  };

  const [currentWeekStart, setCurrentWeekStart] = useState<string>(getMondayOfCurrentWeek());

  const {
    data: timetable,
    isLoading,
  } = useQuery<StudentTimetableResponse>({
    queryKey: ['student-timetable', currentWeekStart],
    queryFn: () => api.student.getTimetable(currentWeekStart),
    staleTime: 60000,
  });

  // Week navigation
  const handlePrevWeek = () => {
    const d = new Date(currentWeekStart);
    d.setDate(d.getDate() - 7);
    setCurrentWeekStart(d.toISOString().split('T')[0]);
  };

  const handleNextWeek = () => {
    const d = new Date(currentWeekStart);
    d.setDate(d.getDate() + 7);
    setCurrentWeekStart(d.toISOString().split('T')[0]);
  };

  const handleThisWeek = () => {
    setCurrentWeekStart(getMondayOfCurrentWeek());
  };

  // Group occurrences by date / day of week
  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  // Map occurrences by date
  const occurrencesByDate = (timetable?.occurrences || []).reduce<Record<string, DatedOccurrence[]>>(
    (acc, occ) => {
      if (!acc[occ.date]) {
        acc[occ.date] = [];
      }
      acc[occ.date].push(occ);
      return acc;
    },
    {}
  );

  // Generate the 6 days of the week starting from currentWeekStart
  const weekDays = Array.from({ length: 6 }).map((_, idx) => {
    const d = new Date(currentWeekStart);
    d.setDate(d.getDate() + idx);
    const dateStr = d.toISOString().split('T')[0];
    return {
      dateStr,
      dayName: daysOfWeek[idx],
      displayDate: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      sessions: occurrencesByDate[dateStr] || [],
    };
  });

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
              Enrolled Weekly Timetable
            </h1>
            <StatusBadge
              status={timetable?.is_published ? 'PUBLISHED' : 'DRAFT'}
              label={timetable?.is_published ? 'Official Release' : 'Unpublished'}
              size="sm"
            />
          </div>
          <div className="flex items-center gap-2 text-xs text-navy-muted mt-1">
            <span>{timetable?.term_name || 'Academic Term'}</span>
            <span>&bull;</span>
            <span className="flex items-center gap-1 font-mono text-teal">
              <Globe className="w-3 h-3" /> {timetable?.term_timezone || 'UTC'}
            </span>
            <span>&bull;</span>
            <span>Server-derived dated occurrences</span>
          </div>
        </div>

        {/* Week Navigation Controls */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handlePrevWeek}
            aria-label="Previous week"
            leftIcon={<ChevronLeft className="w-4 h-4" />}
          >
            Prev
          </Button>

          <Button variant="secondary" size="sm" onClick={handleThisWeek}>
            Current Week
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleNextWeek}
            aria-label="Next week"
            rightIcon={<ChevronRight className="w-4 h-4" />}
          >
            Next
          </Button>
        </div>
      </div>

      {/* Draft Confidentiality Notice (Acceptance: Students cannot see drafts) */}
      {!timetable?.is_published && !isLoading && (
        <div className="p-6 rounded-xl bg-amber-500/10 border border-amber-500/30 text-center space-y-2">
          <Lock className="w-8 h-8 text-amber-700 mx-auto" />
          <h3 className="font-heading font-bold text-amber-950 text-base">
            Timetable Under Coordinator Review
          </h3>
          <p className="text-xs text-amber-900 max-w-md mx-auto leading-relaxed">
            Institutional draft schedules are strictly confidential and undergoing validation.
            Your weekly schedule will automatically display here the instant an authorized coordinator
            publishes the release.
          </p>
        </div>
      )}

      {/* Week Date Span Display */}
      {timetable && (
        <div className="p-3.5 rounded-xl bg-surface border border-border flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 font-medium text-navy">
            <Calendar className="w-4 h-4 text-teal" />
            <span>
              Week starting {timetable.week_start_date}
            </span>
          </div>
          <span className="text-navy-subtle text-[11px]">
            {timetable.occurrences.length} scheduled academic sessions
          </span>
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="py-20 text-center space-y-3">
          <div className="w-8 h-8 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-navy-muted">
            Generating server-derived dated occurrences with timezone calculations...
          </p>
        </div>
      ) : timetable?.is_published ? (
        <div className="space-y-4">
          {weekDays.map((day) => {
            const hasExceptions = day.sessions.some((s) => s.is_cancelled);

            return (
              <Card
                key={day.dateStr}
                title={`${day.dayName} (${day.displayDate})`}
                action={
                  hasExceptions ? (
                    <span className="text-[11px] font-semibold text-coral bg-coral/10 px-2 py-0.5 rounded border border-coral/20 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> Calendar Exception
                    </span>
                  ) : undefined
                }
              >
                {day.sessions.length === 0 ? (
                  <p className="text-xs text-navy-subtle py-2">
                    No classes scheduled on this date.
                  </p>
                ) : (
                  <div className="divide-y divide-border">
                    {day.sessions.map((sess, idx) => (
                      <div
                        key={idx}
                        className={`py-3.5 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                          sess.is_cancelled ? 'opacity-60 line-through bg-coral/5 p-2 rounded' : ''
                        }`}
                      >
                        <div className="flex items-start sm:items-center gap-3">
                          <div
                            className={`p-2 rounded-lg font-mono font-semibold text-xs shrink-0 flex items-center gap-1.5 ${
                              sess.is_cancelled
                                ? 'bg-coral/10 text-coral'
                                : 'bg-teal-light text-teal'
                            }`}
                          >
                            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                            <span>
                              {sess.start_time} - {sess.end_time}
                            </span>
                          </div>

                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className="font-semibold text-navy text-sm">
                                {sess.subject_name || sess.title}
                              </h4>
                              <span className="font-mono text-[11px] px-1.5 py-0.2 rounded bg-bg text-navy-muted border border-border">
                                {sess.subject_code}
                              </span>
                            </div>

                            <div className="text-xs text-navy-subtle flex flex-wrap items-center gap-2 mt-1">
                              <span className="flex items-center gap-1 font-medium text-navy-muted">
                                <MapPin className="w-3.5 h-3.5 text-teal" aria-hidden="true" />
                                {sess.room_name}
                              </span>
                              <span>&bull;</span>
                              <span>{sess.teacher_name}</span>
                              {sess.is_cancelled && (
                                <span className="text-coral font-semibold not-italic">
                                  &bull; Cancelled: {sess.cancellation_reason || 'Academic Holiday'}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <span className="text-xs font-semibold px-2.5 py-1 rounded border self-start sm:self-auto bg-bg border-border text-navy-muted">
                          Period {sess.period + 1}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      ) : null}
    </div>
  );
};
