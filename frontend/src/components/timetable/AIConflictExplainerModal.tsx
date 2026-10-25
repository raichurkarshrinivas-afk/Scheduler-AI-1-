import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  AlertTriangle,
  Lightbulb,
  RefreshCw,
} from 'lucide-react';
import { Dialog } from '../common/Dialog';
import { Button } from '../common/Button';
import { api } from '../../services/api';
import { ExplainCheckerIssuesOut, CheckerIssueExplanation } from '../../types';

export interface AIConflictExplainerModalProps {
  isOpen: boolean;
  onClose: () => void;
  draftId: string;
  violations: any[];
}

export const AIConflictExplainerModal: React.FC<AIConflictExplainerModalProps> = ({
  isOpen,
  onClose,
  draftId,
  violations,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [explanationData, setExplanationData] = useState<ExplainCheckerIssuesOut | null>(null);

  const fetchExplanations = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const resp = await api.ai.explainChecker({
        draft_id: draftId,
        violations: violations,
      });
      setExplanationData(resp);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to explain checker issues.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && draftId) {
      fetchExplanations();
    }
  }, [isOpen, draftId]);

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="AI Schedule Issue Diagnostic & Explanation"
      maxWidth="lg"
      footer={
        <div className="flex items-center justify-between w-full">
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchExplanations}
            isLoading={isLoading}
            className="flex items-center gap-1.5 text-xs text-navy-muted"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Re-analyze</span>
          </Button>
          <Button variant="primary" size="sm" onClick={onClose}>
            Done
          </Button>
        </div>
      }
    >
      <div className="space-y-4 text-xs">
        {/* Advisory Disclaimer Notice */}
        <div className="p-3.5 rounded-xl bg-teal-light/50 border border-teal/20 text-navy space-y-1">
          <div className="flex items-center gap-2 font-semibold text-teal-dark text-xs">
            <Sparkles className="w-4 h-4 text-teal shrink-0" />
            <span>Advisory Diagnostic Explanations</span>
          </div>
          <p className="text-[11px] text-navy-muted leading-relaxed">
            {explanationData?.disclaimer || (
              "Checker explanations are advisory diagnostic candidates. Authoritative solver validation rules take precedence."
            )}
          </p>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-lg bg-coral-light/60 border border-coral/30 text-xs text-coral font-medium flex items-start gap-2" role="alert">
            <AlertTriangle className="w-4 h-4 text-coral shrink-0 mt-0.5" />
            <div className="flex-1">{errorMsg}</div>
          </div>
        )}

        {isLoading ? (
          <div className="p-12 text-center text-xs text-navy-muted space-y-2">
            <RefreshCw className="w-5 h-5 text-teal animate-spin mx-auto" />
            <p>Analyzing checker violation patterns and conflict relationships...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Explanations List */}
            <div className="space-y-3">
              {explanationData?.explanations.map((item: CheckerIssueExplanation, idx: number) => (
                <div key={idx} className="p-4 bg-surface border border-border rounded-xl space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-navy text-xs">
                      {item.summary}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-coral-light text-coral border border-coral/20">
                      {item.rule}
                    </span>
                  </div>

                  {/* Root Cause */}
                  <div className="p-2.5 bg-white rounded-lg border border-border/80 text-[11px] text-navy-muted leading-relaxed">
                    <strong className="block text-navy font-semibold text-[10px] uppercase tracking-wider mb-1">
                      Underlying Cause:
                    </strong>
                    {item.root_cause_explanation}
                  </div>

                  {/* Resolutions */}
                  {item.potential_resolutions.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] font-semibold text-teal uppercase tracking-wider block">
                        Actionable Resolution Candidates:
                      </span>
                      <ul className="space-y-1 pl-4 text-[11px] text-navy-muted list-disc">
                        {item.potential_resolutions.map((res: string, rIdx: number) => (
                          <li key={rIdx}>{res}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}

              {(!explanationData || explanationData.explanations.length === 0) && (
                <div className="p-8 text-center text-xs text-navy-muted">
                  No active conflict violations recorded on this draft.
                </div>
              )}
            </div>

            {/* General Recommendations */}
            {explanationData && explanationData.general_recommendations.length > 0 && (
              <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl space-y-1.5">
                <div className="flex items-center gap-2 text-amber-800 font-semibold text-xs">
                  <Lightbulb className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>General Scheduler Guidance</span>
                </div>
                <ul className="pl-5 space-y-1 text-[11px] text-amber-900 list-disc">
                  {explanationData.general_recommendations.map((rec, rIdx) => (
                    <li key={rIdx}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </Dialog>
  );
};
