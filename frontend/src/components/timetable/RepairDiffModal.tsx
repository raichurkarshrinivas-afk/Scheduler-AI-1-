import React from 'react';
import {
  X,
  History,
  ArrowRight,
  Clock,
  Building,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import { Button } from '../common/Button';
import { AssignmentChange } from '../../types';

interface RepairDiffModalProps {
  isOpen: boolean;
  onClose: () => void;
  changes: AssignmentChange[];
  totalChanges: number;
  status: string;
  isValid: boolean;
  draftRevision: number;
  days: string[];
  periods: Array<{ id: number; label: string }>;
  roomsById: Record<string, string>;
}

export const RepairDiffModal: React.FC<RepairDiffModalProps> = ({
  isOpen,
  onClose,
  changes,
  totalChanges,
  status,
  isValid,
  draftRevision,
  days,
  periods,
  roomsById,
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-navy/40 backdrop-blur-sm flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="diff-modal-title"
    >
      <div className="bg-surface w-full max-w-2xl rounded-2xl shadow-2xl border border-border flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-border flex items-center justify-between bg-bg/30 rounded-t-2xl">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-teal/10 text-teal">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 id="diff-modal-title" className="text-base font-bold text-navy">
                Minimal-Change Repair Diff & Audit
              </h2>
              <p className="text-xs text-navy-muted">
                Applied to Draft Revision #{draftRevision} &bull; {totalChanges} adjusted assignment{totalChanges === 1 ? '' : 's'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-navy-subtle hover:text-navy hover:bg-bg transition-colors"
            aria-label="Close diff modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Validation Badge & Summary */}
        <div className="p-4 bg-teal-light/40 border-b border-teal/20 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-teal font-medium">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>
              {isValid
                ? 'Constraint Satisfaction Verified: Zero hard conflicts in repaired schedule.'
                : 'Attention: Some constraint issues remain.'}
            </span>
          </div>

          <span className="font-mono text-[11px] font-bold text-navy px-2 py-0.5 rounded bg-surface border border-border">
            Status: {status}
          </span>
        </div>

        {/* Diff Changes Table */}
        <div className="p-4 overflow-y-auto flex-1 text-xs">
          {changes.length === 0 ? (
            <div className="text-center py-8 text-navy-muted">
              <History className="w-8 h-8 mx-auto text-navy-subtle mb-2 opacity-50" />
              <p className="font-semibold">No assignment adjustments needed.</p>
              <p className="text-[11px] mt-1">The schedule was already clean or fully preserved.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {changes.map((c, idx) => {
                const bDay = c.before.day !== undefined ? days[c.before.day] : 'N/A';
                const bPeriod = c.before.period !== undefined ? periods[c.before.period]?.label : 'N/A';
                const bRoom = c.before.room_id ? (roomsById[c.before.room_id] || c.before.room_id) : 'Unassigned';

                const aDay = c.after.day !== undefined ? days[c.after.day] : 'N/A';
                const aPeriod = c.after.period !== undefined ? periods[c.after.period]?.label : 'N/A';
                const aRoom = c.after.room_id ? (roomsById[c.after.room_id] || c.after.room_id) : 'Unassigned';

                return (
                  <div
                    key={idx}
                    className="p-3 rounded-xl border border-border bg-surface hover:border-teal/30 transition-all space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-navy">
                        {c.session_name || c.session_id}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {c.time_moved && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800">
                            <Clock className="w-3 h-3" /> Time Moved
                          </span>
                        )}
                        {c.room_changed && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-800">
                            <Building className="w-3 h-3" /> Room Changed
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                      {/* Before */}
                      <div className="p-2 rounded-lg bg-bg/50 border border-border text-navy-muted">
                        <div className="font-semibold uppercase tracking-wider text-[9px] text-navy-subtle mb-1">
                          Previous Slot
                        </div>
                        <div>
                          {bDay} &bull; {bPeriod}
                        </div>
                        <div className="text-navy-subtle mt-0.5">{bRoom}</div>
                      </div>

                      {/* After */}
                      <div className="p-2 rounded-lg bg-teal-light/60 border border-teal/30 text-teal font-medium">
                        <div className="font-semibold uppercase tracking-wider text-[9px] text-teal/80 mb-1 flex items-center gap-1">
                          <ArrowRight className="w-3 h-3" /> Repaired Slot
                        </div>
                        <div className="text-navy font-semibold">
                          {aDay} &bull; {aPeriod}
                        </div>
                        <div className="text-teal font-medium mt-0.5">{aRoom}</div>
                      </div>
                    </div>

                    <div className="text-[10px] text-navy-subtle flex items-center gap-2 pt-1 border-t border-border/50">
                      <span>Reason: {c.reason}</span>
                      {c.teacher_id && <span>&bull; Teacher: {c.teacher_id}</span>}
                      {c.section_id && <span>&bull; Section: {c.section_id}</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-border flex justify-end bg-bg/20 rounded-b-2xl">
          <Button variant="primary" size="sm" onClick={onClose}>
            Done Reviewing
          </Button>
        </div>
      </div>
    </div>
  );
};
