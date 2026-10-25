import React, { useState } from 'react';
import {
  AlertTriangle,
  Sparkles,
  CheckCircle2,
  Wrench,
  ChevronDown,
  ChevronUp,
  History,
  Info,
} from 'lucide-react';
import { Button } from '../common/Button';
import { TimetableViolation } from '../../types';

interface ConflictBannerProps {
  status: string;
  violations: TimetableViolation[];
  onRepair: () => void;
  isRepairing?: boolean;
  onReviewChanges?: () => void;
  changeCount?: number;
  onExplainAI?: () => void;
}

export const ConflictBanner: React.FC<ConflictBannerProps> = ({
  status,
  violations,
  onRepair,
  isRepairing = false,
  onReviewChanges,
  changeCount = 0,
  onExplainAI,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasConflicts = violations.length > 0 || status === 'INVALID';

  if (!hasConflicts) {
    return (
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 rounded-xl border border-teal/30 bg-teal-light/40 text-xs">
        <div className="flex items-center gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-teal shrink-0" aria-hidden="true" />
          <div>
            <span className="font-bold text-teal">Authoritatively Verified Schedule</span>
            <span className="text-navy-muted ml-2">
              All sessions satisfy teacher, room, and student non-overlap constraints.
            </span>
          </div>
        </div>

        {changeCount > 0 && onReviewChanges && (
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<History className="w-3.5 h-3.5" />}
            onClick={onReviewChanges}
            className="text-teal hover:bg-teal/10"
          >
            Review {changeCount} Persisted Changes
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-coral/30 bg-coral/5 p-3.5 space-y-2 text-xs">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-start sm:items-center gap-2.5">
          <AlertTriangle className="w-4 h-4 text-coral shrink-0 mt-0.5 sm:mt-0" aria-hidden="true" />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-coral-dark">
                {violations.length} Institutional Conflicts Detected
              </span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-coral/15 text-coral uppercase tracking-wider">
                Publication Blocked
              </span>
            </div>
            <p className="text-navy-muted text-[11px] mt-0.5">
              Draft contains resource double-booking, availability, or capacity violations.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          {changeCount > 0 && onReviewChanges && (
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<History className="w-3.5 h-3.5" />}
              onClick={onReviewChanges}
            >
              Diff ({changeCount})
            </Button>
          )}

          {onExplainAI && (
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Sparkles className="w-3.5 h-3.5 text-teal" />}
              onClick={onExplainAI}
            >
              Explain with AI
            </Button>
          )}

          <Button
            variant="primary"
            size="sm"
            leftIcon={<Wrench className="w-3.5 h-3.5" />}
            onClick={onRepair}
            isLoading={isRepairing}
          >
            Minimal-Change Repair
          </Button>

          {violations.length > 0 && (
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 rounded text-navy-subtle hover:text-navy hover:bg-coral/10 transition-colors"
              aria-label={isExpanded ? 'Collapse conflict details' : 'Expand conflict details'}
            >
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Expandable Conflict Details */}
      {isExpanded && violations.length > 0 && (
        <div className="mt-2 pt-2 border-t border-coral/20">
          <ul className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
            {violations.map((v, idx) => (
              <li
                key={idx}
                className="flex items-start gap-2 p-1.5 rounded bg-surface/80 border border-coral/20 text-[11px]"
              >
                <Info className="w-3.5 h-3.5 text-coral shrink-0 mt-0.5" aria-hidden="true" />
                <div className="min-w-0">
                  <span className="font-semibold text-coral-dark mr-1.5">[{v.rule}]</span>
                  <span className="text-navy">{v.message}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
