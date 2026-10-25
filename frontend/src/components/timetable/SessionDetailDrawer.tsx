import React, { useState, useEffect } from 'react';
import {
  X,
  Lock,
  Unlock,
  MoveRight,
  BookOpen,
  Laptop,
  User,
  Users,
  Building,
  Check,
  AlertCircle,
} from 'lucide-react';
import { Button } from '../common/Button';
import { TimetableAssignment } from '../../types';
import { SessionMeta } from './SessionCard';

interface RoomOption {
  id: string;
  name: string;
  capacity?: number;
  room_type?: string;
  features?: string[];
}

interface SessionDetailDrawerProps {
  assignment: TimetableAssignment | null;
  meta: SessionMeta | null;
  rooms: RoomOption[];
  days: string[];
  periods: Array<{ id: number; label: string }>;
  isOpen: boolean;
  onClose: () => void;
  onMove: (day: number, period: number, roomId: string) => Promise<void>;
  onToggleLock: (locked: boolean) => Promise<void>;
  isSaving?: boolean;
  isReadOnly?: boolean;
}

export const SessionDetailDrawer: React.FC<SessionDetailDrawerProps> = ({
  assignment,
  meta,
  rooms,
  days,
  periods,
  isOpen,
  onClose,
  onMove,
  onToggleLock,
  isSaving = false,
  isReadOnly = false,
}) => {
  const [selectedDay, setSelectedDay] = useState<number>(0);
  const [selectedPeriod, setSelectedPeriod] = useState<number>(0);
  const [selectedRoom, setSelectedRoom] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (assignment) {
      setSelectedDay(assignment.day);
      setSelectedPeriod(assignment.period);
      setSelectedRoom(assignment.room_id);
      setErrorMessage(null);
    }
  }, [assignment]);

  if (!isOpen || !assignment || !meta) return null;

  const isPractical = meta.type === 'PRACTICAL';
  const isLocked = Boolean(assignment.is_locked);

  const handleApplyMove = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    try {
      await onMove(selectedDay, selectedPeriod, selectedRoom);
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to move session.');
    }
  };

  const handleLockToggle = async () => {
    try {
      await onToggleLock(!isLocked);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update lock status.');
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-navy/30 backdrop-blur-sm flex justify-end transition-opacity"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
    >
      <div className="bg-surface w-full max-w-md h-full shadow-2xl flex flex-col border-l border-border animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-4 border-b border-border flex items-start justify-between bg-bg/40">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-teal bg-teal/10 px-2 py-0.5 rounded">
                {meta.code}
              </span>
              <span
                className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                  isPractical ? 'bg-indigo-100 text-indigo-700' : 'bg-teal-light text-teal'
                }`}
              >
                {isPractical ? (
                  <Laptop className="w-3 h-3" />
                ) : (
                  <BookOpen className="w-3 h-3" />
                )}
                {meta.type}
              </span>
            </div>
            <h2 id="drawer-title" className="text-base font-bold text-navy mt-1">
              {meta.name}
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-navy-subtle hover:text-navy hover:bg-bg transition-colors"
            aria-label="Close detail panel"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-5 flex-1 overflow-y-auto text-xs">
          {/* Metadata Cards */}
          <div className="grid grid-cols-2 gap-2.5">
            <div className="p-3 rounded-lg border border-border bg-bg/30">
              <div className="flex items-center gap-1.5 text-navy-muted mb-1 text-[11px]">
                <User className="w-3.5 h-3.5" />
                <span>Instructor</span>
              </div>
              <div className="font-semibold text-navy">
                {meta.teacherName || 'Assigned Staff'}
              </div>
            </div>

            <div className="p-3 rounded-lg border border-border bg-bg/30">
              <div className="flex items-center gap-1.5 text-navy-muted mb-1 text-[11px]">
                <Users className="w-3.5 h-3.5" />
                <span>Cohort / Section</span>
              </div>
              <div className="font-semibold text-navy">
                {meta.sectionName || 'Class Group'}
              </div>
            </div>

            <div className="p-3 rounded-lg border border-border bg-bg/30">
              <div className="flex items-center gap-1.5 text-navy-muted mb-1 text-[11px]">
                <Building className="w-3.5 h-3.5" />
                <span>Current Facility</span>
              </div>
              <div className="font-semibold text-navy">
                {meta.roomName || assignment.room_id}
              </div>
            </div>

            <div className="p-3 rounded-lg border border-border bg-bg/30">
              <div className="flex items-center gap-1.5 text-navy-muted mb-1 text-[11px]">
                <span>Duration</span>
              </div>
              <div className="font-semibold text-navy">
                {meta.duration} hour{meta.duration > 1 ? 's' : ''} ({periods[assignment.period]?.label || `Period ${assignment.period}`})
              </div>
            </div>
          </div>

          {/* Locked Assignment Status & Toggle */}
          <div className="p-3.5 rounded-lg border border-border bg-surface flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div
                className={`p-2 rounded-lg ${
                  isLocked ? 'bg-teal/10 text-teal' : 'bg-bg text-navy-subtle'
                }`}
              >
                {isLocked ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
              </div>
              <div>
                <div className="font-semibold text-navy">
                  {isLocked ? 'Locked Commitment' : 'Flexible Assignment'}
                </div>
                <div className="text-[11px] text-navy-muted">
                  {isLocked
                    ? 'Solver & repairs will keep this slot fixed.'
                    : 'Can be shifted during automated schedule repair.'}
                </div>
              </div>
            </div>

            {!isReadOnly && (
              <Button
                variant={isLocked ? 'secondary' : 'primary'}
                size="sm"
                onClick={handleLockToggle}
                isLoading={isSaving}
              >
                {isLocked ? 'Unlock' : 'Lock Slot'}
              </Button>
            )}
          </div>

          {/* Move Session Form (Keyboard / Non-Drag Accessible Alternative) */}
          {!isReadOnly && (
            <div className="border border-border rounded-xl p-3.5 bg-bg/20 space-y-3">
              <div className="flex items-center gap-1.5 text-navy font-bold">
                <MoveRight className="w-4 h-4 text-teal" />
                <span>Move Session (Non-Drag Action)</span>
              </div>
              <p className="text-[11px] text-navy-muted">
                Keyboard-accessible alternative to drag and drop. Select target day, period, and room.
              </p>

              {errorMessage && (
                <div className="p-2.5 rounded-lg bg-coral/10 border border-coral/30 text-coral-dark text-xs flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-coral shrink-0 mt-0.5" />
                  <span>{errorMessage}</span>
                </div>
              )}

              <form onSubmit={handleApplyMove} className="space-y-3">
                <div>
                  <label htmlFor="select-day" className="block text-[11px] font-semibold text-navy-muted mb-1">
                    Target Day
                  </label>
                  <select
                    id="select-day"
                    value={selectedDay}
                    onChange={(e) => setSelectedDay(Number(e.target.value))}
                    className="w-full bg-surface border border-border rounded-lg px-2.5 py-1.5 text-xs text-navy focus:outline-2 focus:outline-teal"
                  >
                    {days.map((dName, dIdx) => (
                      <option key={dIdx} value={dIdx}>
                        {dName}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="select-period" className="block text-[11px] font-semibold text-navy-muted mb-1">
                    Target Time Period
                  </label>
                  <select
                    id="select-period"
                    value={selectedPeriod}
                    onChange={(e) => setSelectedPeriod(Number(e.target.value))}
                    className="w-full bg-surface border border-border rounded-lg px-2.5 py-1.5 text-xs text-navy focus:outline-2 focus:outline-teal"
                  >
                    {periods.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="select-room" className="block text-[11px] font-semibold text-navy-muted mb-1">
                    Target Room / Laboratory
                  </label>
                  <select
                    id="select-room"
                    value={selectedRoom}
                    onChange={(e) => setSelectedRoom(e.target.value)}
                    className="w-full bg-surface border border-border rounded-lg px-2.5 py-1.5 text-xs text-navy focus:outline-2 focus:outline-teal"
                  >
                    {rooms.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} (Cap: {r.capacity || 'N/A'}{r.room_type ? ` • ${r.room_type}` : ''})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="pt-2 flex justify-end gap-2">
                  <Button variant="ghost" size="sm" onClick={onClose} type="button">
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    type="submit"
                    isLoading={isSaving}
                    leftIcon={<Check className="w-3.5 h-3.5" />}
                  >
                    Apply Move
                  </Button>
                </div>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
