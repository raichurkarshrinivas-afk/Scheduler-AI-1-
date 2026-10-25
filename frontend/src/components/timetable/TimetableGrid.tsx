import React, { useState } from 'react';
import { Clock, Coffee } from 'lucide-react';
import { TimetableAssignment } from '../../types';
import { SessionCard, SessionMeta } from './SessionCard';

interface TimePeriod {
  id: number;
  label: string;
  isBreak?: boolean;
}

interface TimetableGridProps {
  days: string[];
  periods: TimePeriod[];
  breakPeriods: number[];
  assignments: TimetableAssignment[];
  sessionMetaById: Record<string, SessionMeta>;
  conflictingSessionIds: Set<string>;
  onSelectSession: (assignment: TimetableAssignment) => void;
  onMoveAssignment: (sessionId: string, targetDay: number, targetPeriod: number) => void;
  onToggleLock: (sessionId: string, currentLock: boolean) => void;
  isReadOnly?: boolean;
}

export const TimetableGrid: React.FC<TimetableGridProps> = ({
  days,
  periods,
  breakPeriods,
  assignments,
  sessionMetaById,
  conflictingSessionIds,
  onSelectSession,
  onMoveAssignment,
  onToggleLock,
  isReadOnly = false,
}) => {
  const [draggedSessionId, setDraggedSessionId] = useState<string | null>(null);
  const [dragOverSlot, setDragOverSlot] = useState<{ day: number; period: number } | null>(null);

  // Group assignments by (day, period)
  const assignmentsBySlot: Record<string, TimetableAssignment[]> = {};
  assignments.forEach((a) => {
    const key = `${a.day}-${a.period}`;
    if (!assignmentsBySlot[key]) {
      assignmentsBySlot[key] = [];
    }
    assignmentsBySlot[key].push(a);
  });

  const handleDragStart = (e: React.DragEvent, sessionId: string) => {
    e.dataTransfer.setData('text/plain', sessionId);
    e.dataTransfer.effectAllowed = 'move';
    setDraggedSessionId(sessionId);
  };

  const handleDragEnd = () => {
    setDraggedSessionId(null);
    setDragOverSlot(null);
  };

  const handleDragOver = (e: React.DragEvent, day: number, period: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (!dragOverSlot || dragOverSlot.day !== day || dragOverSlot.period !== period) {
      setDragOverSlot({ day, period });
    }
  };

  const handleDragLeave = () => {
    setDragOverSlot(null);
  };

  const handleDrop = (e: React.DragEvent, day: number, period: number) => {
    e.preventDefault();
    const sessionId = e.dataTransfer.getData('text/plain') || draggedSessionId;
    setDragOverSlot(null);
    setDraggedSessionId(null);

    if (sessionId) {
      onMoveAssignment(sessionId, day, period);
    }
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-sm">
      <table className="w-full text-left text-xs border-collapse min-w-[800px]">
        <thead>
          <tr className="border-b border-border bg-bg/60 text-navy-muted uppercase font-bold text-[10px] tracking-wider">
            <th className="p-3 w-36 border-r border-border text-center">
              Period / Time
            </th>
            {days.map((day) => (
              <th
                key={day}
                className="p-3 border-r border-border last:border-r-0 text-center font-bold text-navy"
              >
                {day}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {periods.map((period) => {
            const isBreak = breakPeriods.includes(period.id) || period.isBreak;

            if (isBreak) {
              return (
                <tr
                  key={`break-${period.id}`}
                  className="bg-bg/80 border-y border-border/80"
                >
                  <td className="p-2.5 text-center font-semibold text-navy-muted bg-bg/90 border-r border-border flex items-center justify-center gap-1.5">
                    <Coffee className="w-3.5 h-3.5 text-amber-700" />
                    <span>{period.label}</span>
                  </td>
                  <td
                    colSpan={days.length}
                    className="p-2 text-center text-navy-subtle font-medium text-[11px] bg-amber-500/5 select-none"
                  >
                    <span className="inline-flex items-center gap-1.5 text-amber-800 font-semibold px-2.5 py-0.5 rounded-full bg-amber-100/60">
                      <Coffee className="w-3 h-3" /> Campus Lunch & Institutional Recess Window
                    </span>
                  </td>
                </tr>
              );
            }

            return (
              <tr key={period.id} className="hover:bg-bg/20 transition-colors">
                {/* Time slot header */}
                <td className="p-3 font-semibold text-navy-muted bg-bg/40 border-r border-border text-center flex flex-col items-center justify-center min-h-[90px]">
                  <div className="flex items-center gap-1 text-navy font-bold text-[11px]">
                    <Clock className="w-3.5 h-3.5 text-teal" />
                    <span>Period {period.id + 1}</span>
                  </div>
                  <span className="text-[10px] text-navy-subtle mt-0.5">
                    {period.label}
                  </span>
                </td>

                {/* Day cells */}
                {days.map((_, dayIdx) => {
                  const slotKey = `${dayIdx}-${period.id}`;
                  const slotAssignments = assignmentsBySlot[slotKey] || [];
                  const isOver =
                    dragOverSlot &&
                    dragOverSlot.day === dayIdx &&
                    dragOverSlot.period === period.id;

                  return (
                    <td
                      key={dayIdx}
                      onDragOver={(e) => handleDragOver(e, dayIdx, period.id)}
                      onDragLeave={handleDragLeave}
                      onDrop={(e) => handleDrop(e, dayIdx, period.id)}
                      className={`p-2 border-r border-border last:border-r-0 align-top transition-colors relative min-w-[130px] ${
                        isOver
                          ? 'bg-teal-light/40 ring-2 ring-teal ring-inset rounded'
                          : 'bg-surface'
                      }`}
                    >
                      <div className="space-y-1.5 min-h-[70px] flex flex-col justify-start">
                        {slotAssignments.map((assign) => {
                          const meta = sessionMetaById[assign.session_id] || {
                            id: assign.session_id,
                            name: `Session ${assign.session_id}`,
                            code: 'SESS',
                            type: 'THEORY',
                            duration: assign.duration || 1,
                            roomName: assign.room_id,
                            teacherName: assign.teacher_id,
                            sectionName: assign.section_id,
                          };

                          const hasConflict = conflictingSessionIds.has(assign.session_id);

                          return (
                            <SessionCard
                              key={assign.session_id}
                              assignment={assign}
                              meta={meta}
                              hasConflict={hasConflict}
                              isDragging={draggedSessionId === assign.session_id}
                              onSelect={() => onSelectSession(assign)}
                              onDragStart={(e) => handleDragStart(e, assign.session_id)}
                              onDragEnd={handleDragEnd}
                              onToggleLock={() => {
                                onToggleLock(assign.session_id, Boolean(assign.is_locked));
                              }}
                              isReadOnly={isReadOnly}
                            />
                          );
                        })}

                        {slotAssignments.length === 0 && (
                          <div
                            className={`h-full min-h-[60px] rounded-lg border border-dashed flex items-center justify-center transition-opacity ${
                              isOver
                                ? 'border-teal bg-teal-light/50 text-teal font-semibold'
                                : 'border-border/60 hover:border-border text-navy-subtle/30 hover:text-navy-subtle'
                            }`}
                          >
                            <span className="text-[10px] select-none">
                              {isOver ? 'Drop here' : 'Unallocated'}
                            </span>
                          </div>
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
