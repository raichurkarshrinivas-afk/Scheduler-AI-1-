import React, { useState } from 'react';
import {
  Sparkles,
  AlertTriangle,
  FileSpreadsheet,
  ArrowRight,
} from 'lucide-react';
import { Dialog } from './Dialog';
import { Button } from './Button';
import { FormField, Textarea } from './FormField';
import { api } from '../../services/api';
import { ColumnMappingProposalOut } from '../../types';

export interface AIColumnMappingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AIColumnMappingModal: React.FC<AIColumnMappingModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [headersText, setHeadersText] = useState(
    'Course Code, Course Title, Faculty Instructor, Hall Name, Max Capacity, Day of Week, Time Slot, Miscellaneous Notes'
  );
  const [isProposing, setIsProposing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<ColumnMappingProposalOut | null>(null);

  const handlePropose = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setResult(null);

    const headers = headersText
      .split(/[,\n]/)
      .map((h) => h.trim())
      .filter((h) => h.length > 0);

    if (headers.length === 0) {
      setErrorMsg('Please enter at least one column header name.');
      return;
    }

    setIsProposing(true);
    try {
      const resp = await api.ai.proposeMappings({
        headers: headers,
        sample_rows: [
          ['CS101', 'Intro to Computing', 'Dr. Alan Turing', 'LT-01', '120', 'Monday', 'Period 1', 'Note A'],
        ],
      });
      setResult(resp);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to propose column mappings.');
    } finally {
      setIsProposing(false);
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="AI Import Column Mapping Assistant"
      maxWidth="lg"
      footer={
        <div className="flex items-center justify-between w-full">
          <span className="text-[11px] text-navy-subtle">
            All mappings are advisory and must be verified by an administrator.
          </span>
          <Button variant="primary" size="sm" onClick={onClose}>
            Done
          </Button>
        </div>
      }
    >
      <div className="space-y-4 text-xs">
        <div className="p-3.5 rounded-xl bg-teal-light/50 border border-teal/20 text-navy space-y-1">
          <div className="flex items-center gap-2 font-semibold text-teal-dark text-xs">
            <Sparkles className="w-4 h-4 text-teal shrink-0" />
            <span>Automated Tabular Schema Mapping</span>
          </div>
          <p className="text-[11px] text-navy-muted leading-relaxed">
            {result?.disclaimer || (
              "Proposed column mappings must be verified by an administrator before importing data. Sensitive cell values like student identifiers are sanitized automatically."
            )}
          </p>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-lg bg-coral-light/60 border border-coral/30 text-xs text-coral font-medium flex items-start gap-2" role="alert">
            <AlertTriangle className="w-4 h-4 text-coral shrink-0 mt-0.5" />
            <div className="flex-1">{errorMsg}</div>
          </div>
        )}

        <form onSubmit={handlePropose} className="space-y-3">
          <FormField
            label="Raw CSV / Excel Column Headers (Comma or Line Separated)"
            htmlFor="headers-input"
            helperText="Enter column headers from your institutional spreadsheet to map to system schema"
          >
            <Textarea
              id="headers-input"
              rows={3}
              value={headersText}
              onChange={(e) => setHeadersText(e.target.value)}
              className="font-mono text-xs"
              required
            />
          </FormField>

          <div className="flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isProposing}
              className="flex items-center gap-1.5"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Propose Schema Mappings</span>
            </Button>
          </div>
        </form>

        {result && (
          <div className="space-y-4 pt-3 border-t border-border animate-in fade-in-50 duration-200">
            {/* Unmapped Warnings */}
            {result.unmapped_headers.length > 0 && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-1">
                <span className="font-semibold text-amber-800 text-[11px] block">
                  Unmapped Headers ({result.unmapped_headers.length})
                </span>
                <p className="text-[11px] text-amber-900">
                  The following columns could not be mapped with high confidence: <strong>{result.unmapped_headers.join(', ')}</strong>. These columns will be skipped during import.
                </p>
              </div>
            )}

            {/* Mappings Table */}
            <div className="space-y-1.5">
              <label className="block text-[11px] font-semibold text-navy uppercase tracking-wider">
                Proposed Schema Field Alignments
              </label>

              <div className="divide-y divide-border border border-border rounded-xl overflow-hidden bg-white">
                {Object.entries(result.mappings).map(([header, targetField]) => {
                  const conf = result.confidences[header] || 0;
                  const isMapped = !!targetField;

                  return (
                    <div key={header} className="p-3 flex items-center justify-between text-xs">
                      <div className="font-mono font-semibold text-navy">
                        {header}
                      </div>

                      <ArrowRight className="w-3.5 h-3.5 text-navy-subtle shrink-0" />

                      <div className="flex items-center gap-3">
                        {isMapped ? (
                          <span className="font-mono px-2 py-0.5 rounded bg-teal-light text-teal font-bold text-[11px]">
                            {targetField}
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded bg-bg text-navy-subtle text-[11px] italic">
                            Unmapped
                          </span>
                        )}

                        <span className={`text-[10px] font-bold ${conf >= 0.9 ? 'text-teal' : conf > 0.5 ? 'text-amber-600' : 'text-navy-subtle'}`}>
                          {(conf * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </Dialog>
  );
};
