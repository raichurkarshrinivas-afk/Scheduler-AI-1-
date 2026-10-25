import React from 'react';
import { Lock, Unlock, AlertTriangle, BookOpen, Laptop, GripVertical } from 'lucide-react';
import { TimetableAssignment } from '../../types';

export interface SessionMeta {
  id: string;
  name: string;
  code: string;
  type: 'THEORY' | 'PRACTICAL' | 'TUTORIAL';
  duration: number;
  teacherName?: string;
  roomName?: string;
  sectionName?: string;
}

interface SessionCardProps {
  assignment: TimetableAssignment;
  meta: SessionMeta;
  hasConflict?: boolean;
  isDragging?: boolean;
  onSelect: () => void;
  onDragStart?: (e: React.DragEvent) => void;
  onDragEnd?: (e: React.DragEvent) => void;
  onToggleLock?: (e: React.MouseEvent) => void;
  isReadOnly?: boolean;
}

export const SessionCard: React.FC<SessionCardProps> = ({
  assignment,
  meta,
  hasConflict = false,
  isDragging = false,
  onSelect,
  onDragStart,
  onDragEnd,
  onToggleLock,
  isReadOnly = false,
}) => {
  const isPractical = meta.type === 'PRACTICAL';
  const isLocked = Boolean(assignment.is_locked);

  // Visual style variants: Theory (teal/ice) vs Practical (indigo/navy) vs Conflict (coral)
  const cardBorder = hasConflict
    ? 'border-coral ring-1 ring-coral/40 bg-coral/5 shadow-coral/10'
    : isPractical
    ? 'border-indigo-400/40 bg-indigo-50/70 hover:bg-indigo-50 hover:border-indigo-500/60 shadow-sm'
    : 'border-teal/30 bg-teal-light/50 hover:bg-teal-light hover:border-teal/50 shadow-sm';

  const titleColor = hasConflict
    ? 'text-coral-dark font-bold'
    : isPractical
    ? 'text-indigo-950 font-bold'
    : 'text-teal font-bold';

  const badgeBg = isPractical
    ? 'bg-indigo-600/10 text-indigo-700'
    : 'bg-teal/10 text-teal';

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${meta.name} in ${meta.roomName || 'unassigned'} taught by ${meta.teacherName || 'unassigned'}`}
      draggable={!isReadOnly}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
      className={`relative group rounded-lg p-2.5 transition-all duration-150 border text-xs cursor-pointer select-none ${cardBorder} ${
        isDragging ? 'opacity-40 scale-95 border-dashed border-teal' : 'hover:-translate-y-0.5'
      }`}
    >
      {/* Header: Type icon & Locked status */}
      <div className="flex items-center justify-between gap-1 mb-1.5">
        <div className="flex items-center gap-1.5 min-w-0">
          {!isReadOnly && (
            <span
              className="text-navy-subtle/50 group-hover:text-navy cursor-grab active:cursor-grabbing -ml-1"
              title="Drag to reschedule"
              aria-hidden="true"
            >
              <GripVertical className="w-3.5 h-3.5" />
            </span>
          )}

          <span
            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${badgeBg}`}
          >
            {isPractical ? (
              <Laptop className="w-3 h-3" aria-hidden="true" />
            ) : (
              <BookOpen className="w-3 h-3" aria-hidden="true" />
            )}
            <span>{isPractical ? `${meta.duration}h Lab` : 'Lecture'}</span>
          </span>

          <span className="font-mono text-[11px] font-semibold text-navy-muted truncate">
            {meta.code}
          </span>
        </div>

        <div className="flex items-center gap-1">
          {hasConflict && (
            <span
              className="inline-flex items-center text-coral animate-pulse"
              title="Schedule collision detected"
              aria-label="Conflict detected"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
            </span>
          )}

          {!isReadOnly && onToggleLock && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onToggleLock(e);
              }}
              className={`p-1 rounded transition-colors ${
                isLocked
                  ? 'text-teal bg-teal/10 hover:bg-teal/20'
                  : 'text-navy-subtle/40 hover:text-navy hover:bg-bg'
              }`}
              title={isLocked ? 'Locked assignment (Click to unlock)' : 'Click to lock in place'}
              aria-label={isLocked ? 'Unlock session' : 'Lock session'}
            >
              {isLocked ? (
                <Lock className="w-3 h-3" />
              ) : (
                <Unlock className="w-3 h-3 opacity-0 group-hover:opacity-100" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Course Title */}
      <div className={`truncate text-xs ${titleColor}`} title={meta.name}>
        {meta.name}
      </div>

      {/* Meta details: Room, Teacher, Cohort */}
      <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-navy-muted">
        <span className="font-medium text-navy/80">
          {meta.roomName || assignment.room_id}
        </span>
        {meta.teacherName && (
          <>
            <span className="text-navy-subtle/40" aria-hidden="true">&bull;</span>
            <span className="truncate">{meta.teacherName}</span>
          </>
        )}
        {meta.sectionName && (
          <>
            <span className="text-navy-subtle/40" aria-hidden="true">&bull;</span>
            <span className="text-navy-subtle font-mono text-[10px]">
              {meta.sectionName}
            </span>
          </>
        )}
      </div>
    </div>
  );
};
