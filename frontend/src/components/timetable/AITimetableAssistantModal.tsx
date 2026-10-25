import React, { useState } from 'react';
import {
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Send,
  Lock,
} from 'lucide-react';
import { Dialog } from '../common/Dialog';
import { Button } from '../common/Button';
import { FormField, Textarea } from '../common/FormField';
import { api } from '../../services/api';
import {
  TimetableInterpretationResponse,
  ResolvedSessionChange,
} from '../../types';

export interface AITimetableAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  draftId: string;
  draftRevision: number;
  onChangesApplied: () => void;
}

export const AITimetableAssistantModal: React.FC<AITimetableAssistantModalProps> = ({
  isOpen,
  onClose,
  draftId,
  draftRevision,
  onChangesApplied,
}) => {
  const [requestText, setRequestText] = useState('');
  const [isInterpreting, setIsInterpreting] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [interpretation, setInterpretation] = useState<TimetableInterpretationResponse | null>(null);
  const [applySuccessMsg, setApplySuccessMsg] = useState<string | null>(null);

  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  const handleInterpret = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setInterpretation(null);
    setApplySuccessMsg(null);

    if (requestText.trim().length < 3) {
      setErrorMsg('Please enter a timetable change request of at least 3 characters.');
      return;
    }

    setIsInterpreting(true);
    try {
      const resp = await api.ai.interpretChange({
        draft_id: draftId,
        request_text: requestText.trim(),
      });
      setInterpretation(resp);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to interpret change request.');
    } finally {
      setIsInterpreting(false);
    }
  };

  const handleApply = async () => {
    if (!interpretation || interpretation.proposed_changes.length === 0) return;
    setIsApplying(true);
    setErrorMsg(null);
    try {
      const resp = await api.ai.applyChange({
        draft_id: interpretation.draft_id || draftId,
        expected_revision: interpretation.draft_revision || draftRevision,
        changes: interpretation.proposed_changes,
      });

      setApplySuccessMsg(resp.message);
      onChangesApplied();
      setTimeout(() => {
        onClose();
        setInterpretation(null);
        setRequestText('');
        setApplySuccessMsg(null);
      }, 1800);
    } catch (err: any) {
      if (err.message && err.message.includes('409')) {
        setErrorMsg('Stale draft conflict: The timetable draft was updated concurrently. Please refresh the workspace and re-interpret.');
      } else {
        setErrorMsg(err.message || 'Failed to apply candidate changes.');
      }
    } finally {
      setIsApplying(false);
    }
  };

  const setExample = (text: string) => {
    setRequestText(text);
    setErrorMsg(null);
    setInterpretation(null);
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="AI Timetable Interpretation Assistant"
      maxWidth="lg"
      footer={
        <div className="flex items-center justify-between w-full">
          <div className="text-[11px] text-navy-subtle flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-navy-subtle" />
            <span>Changes applied as uncommitted draft edits. Publication is never automated.</span>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={onClose} disabled={isApplying}>
              Cancel
            </Button>
            {interpretation && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleApply}
                isLoading={isApplying}
                disabled={interpretation.proposed_changes.length === 0}
                className="flex items-center gap-1.5"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Approve & Apply to Draft</span>
              </Button>
            )}
          </div>
        </div>
      }
    >
      <div className="space-y-4 text-xs">
        {/* Critical Disclaimer Notice */}
        <div className="p-3.5 rounded-xl bg-teal-light/50 border border-teal/20 text-navy space-y-1">
          <div className="flex items-center gap-2 font-semibold text-teal-dark text-xs">
            <Sparkles className="w-4 h-4 text-teal shrink-0" />
            <span>Advisory Diagnostic & Interpretation Tool</span>
          </div>
          <p className="text-[11px] text-navy-muted leading-relaxed">
            Candidate suggestions are <strong>unverified interpretations</strong> of natural language requests. You must review the proposed changes and run authoritative solver checks before publishing. Confidential student records and passwords are never collected or sent.
          </p>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-lg bg-coral-light/60 border border-coral/30 text-xs text-coral font-medium flex items-start gap-2" role="alert">
            <AlertTriangle className="w-4 h-4 text-coral shrink-0 mt-0.5" />
            <div className="flex-1">{errorMsg}</div>
          </div>
        )}

        {applySuccessMsg && (
          <div className="p-3 rounded-lg bg-teal-light/70 border border-teal/30 text-xs text-teal-dark font-medium flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal shrink-0 mt-0.5" />
            <div>{applySuccessMsg}</div>
          </div>
        )}

        {/* Input Form */}
        <form onSubmit={handleInterpret} className="space-y-3">
          <FormField
            label="Describe Timetable Change Request"
            htmlFor="ai-req-text"
            helperText={`${requestText.length}/2000 characters`}
          >
            <Textarea
              id="ai-req-text"
              rows={3}
              placeholder="e.g. Move Dr. Alan Turing's Friday afternoon CS101 lecture to Tuesday morning in Room 101..."
              value={requestText}
              onChange={(e) => setRequestText(e.target.value)}
              maxLength={2000}
              required
              className="text-xs"
            />
          </FormField>

          {/* Quick Examples */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] text-navy-subtle uppercase font-semibold">Try Quick Example:</span>
            <button
              type="button"
              onClick={() => setExample("Move Dr. Alan Turing CS101 Friday afternoon class to Tuesday morning in Room 101")}
              className="px-2 py-0.5 rounded bg-bg hover:bg-border/60 text-[10px] text-navy-muted border border-border"
            >
              Move Friday afternoon to Tuesday morning
            </button>
            <button
              type="button"
              onClick={() => setExample("Move CS101 lecture to Room 101 on Wednesday period 3 if possible")}
              className="px-2 py-0.5 rounded bg-bg hover:bg-border/60 text-[10px] text-navy-muted border border-border"
            >
              Soft preference for Wednesday period 3
            </button>
          </div>

          <div className="pt-1 flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isInterpreting}
              className="flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Interpret Request</span>
            </Button>
          </div>
        </form>

        {/* Results Panel */}
        {interpretation && (
          <div className="space-y-4 pt-3 border-t border-border animate-in fade-in-50 duration-200">
            {/* Summary & Confidence */}
            <div className="p-3 bg-surface border border-border rounded-xl flex items-center justify-between">
              <div>
                <span className="text-[10px] uppercase font-semibold text-navy-subtle block">
                  Interpreted Action
                </span>
                <p className="font-semibold text-navy text-xs mt-0.5">
                  {interpretation.raw_summary}
                </p>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-navy-subtle uppercase block font-semibold">Confidence</span>
                <span className="text-xs font-bold text-teal">
                  {(interpretation.confidence_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            {/* Explicit Ambiguity Warnings */}
            {interpretation.is_ambiguous && interpretation.ambiguities.length > 0 && (
              <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-amber-800 font-semibold text-xs">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>Ambiguity Warnings ({interpretation.ambiguities.length})</span>
                </div>
                <div className="space-y-1.5 pl-6">
                  {interpretation.ambiguities.map((amb, idx) => (
                    <div key={idx} className="text-[11px] text-amber-900 leading-snug">
                      <strong className="block font-medium">&bull; {amb.description}</strong>
                      <span className="text-amber-700 italic">Suggestion: {amb.suggested_clarification}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Proposed Modifications Diff View */}
            <div className="space-y-1.5">
              <label className="block text-[11px] font-semibold text-navy uppercase tracking-wider">
                Proposed Assignment Modifications
              </label>

              <div className="divide-y divide-border border border-border rounded-xl overflow-hidden bg-white">
                {interpretation.proposed_changes.map((ch: ResolvedSessionChange) => (
                  <div key={ch.session_id} className="p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                    <div>
                      <div className="font-semibold text-navy flex items-center gap-2">
                        <span>{ch.session_name}</span>
                        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-bg text-navy-muted">
                          {ch.course_code}
                        </span>
                      </div>
                      <div className="text-[11px] text-navy-subtle mt-0.5">
                        Teacher: {ch.proposed_teacher_name || 'Unassigned'}
                      </div>
                    </div>

                    <div className="flex items-center gap-3 bg-bg px-3 py-1.5 rounded-lg border border-border/80">
                      <div>
                        <span className="text-[9px] uppercase font-bold text-navy-subtle block">Current</span>
                        <span className="text-[11px] text-navy line-through">
                          {days[ch.original_day] || `Day ${ch.original_day}`}, P{ch.original_period} ({ch.original_room_name || 'Room'})
                        </span>
                      </div>

                      <ArrowRight className="w-4 h-4 text-teal shrink-0" />

                      <div>
                        <span className="text-[9px] uppercase font-bold text-teal block">Proposed</span>
                        <span className="text-[11px] font-bold text-navy">
                          {days[ch.proposed_day] || `Day ${ch.proposed_day}`}, P{ch.proposed_period} ({ch.proposed_room_name || 'Room'})
                        </span>
                      </div>
                    </div>
                  </div>
                ))}

                {interpretation.proposed_changes.length === 0 && (
                  <div className="p-4 text-center text-xs text-navy-muted">
                    No matching sessions could be resolved from your input prompt.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </Dialog>
  );
};
