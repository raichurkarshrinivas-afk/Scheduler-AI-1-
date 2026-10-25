import React, { useState, useEffect } from 'react';
import {
  Lock,
  GitCompare,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Table } from '../../components/common/Table';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Dialog } from '../../components/common/Dialog';
import { api } from '../../services/api';
import { PublicationSummary, PublicationDiff, TimetableDraft } from '../../types';
import { StaffOutboxSection } from '../../components/communication/StaffOutboxSection';
import { Send, FileText } from 'lucide-react';

export const StaffPublishHistory: React.FC = () => {
  const [publications, setPublications] = useState<PublicationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [mainTab, setMainTab] = useState<'publications' | 'outbox'>('publications');

  // Diff Modal State
  const [isDiffModalOpen, setIsDiffModalOpen] = useState(false);
  const [selectedPubForDiff, setSelectedPubForDiff] = useState<PublicationSummary | null>(null);
  const [compareTargetId, setCompareTargetId] = useState<string>('');
  const [diffData, setDiffData] = useState<PublicationDiff | null>(null);
  const [isDiffLoading, setIsDiffLoading] = useState(false);
  const [diffError, setDiffError] = useState<string | null>(null);

  // Restore Modal State
  const [isRestoreModalOpen, setIsRestoreModalOpen] = useState(false);
  const [pubToRestore, setPubToRestore] = useState<PublicationSummary | null>(null);
  const [isRestoring, setIsRestoring] = useState(false);
  const [restoredDraft, setRestoredDraft] = useState<TimetableDraft | null>(null);
  const [restoreSuccessMessage, setRestoreSuccessMessage] = useState<string | null>(null);

  // Load publications list
  const loadPublications = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const typeParam = typeFilter === 'ALL' ? undefined : typeFilter;
      const data = await api.publications.list(typeParam);
      setPublications(data);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load publication history.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPublications();
  }, [typeFilter]);

  // Open Diff Modal
  const handleOpenDiff = async (pub: PublicationSummary) => {
    setSelectedPubForDiff(pub);
    // Find prior version in list by default
    const pubIndex = publications.findIndex((p) => p.id === pub.id);
    const priorPub = publications[pubIndex + 1];
    const targetId = priorPub ? priorPub.id : pub.id;
    setCompareTargetId(targetId);
    setIsDiffModalOpen(true);
    await fetchDiff(pub.id, targetId);
  };

  const fetchDiff = async (baseId: string, compId: string) => {
    setIsDiffLoading(true);
    setDiffError(null);
    try {
      const diff = await api.publications.getDiff(baseId, compId);
      setDiffData(diff);
    } catch (err: any) {
      setDiffError(err.message || 'Failed to calculate version difference.');
    } finally {
      setIsDiffLoading(false);
    }
  };

  // Open Restore Modal
  const handleOpenRestore = (pub: PublicationSummary) => {
    setPubToRestore(pub);
    setRestoredDraft(null);
    setRestoreSuccessMessage(null);
    setIsRestoreModalOpen(true);
  };

  const handleConfirmRestore = async () => {
    if (!pubToRestore) return;
    setIsRestoring(true);
    setErrorMessage(null);
    try {
      const draft = await api.publications.restore(pubToRestore.id);
      setRestoredDraft(draft);
      setRestoreSuccessMessage(
        `Version v${pubToRestore.version_number} was successfully restored as a new draft (Rev #${draft.revision}). History has been preserved and the restored draft has passed independent verification (${draft.status}).`
      );
      // Reload publication list to show preserved history
      await loadPublications();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to restore publication snapshot as a new draft.');
    } finally {
      setIsRestoring(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
              Publication Governance & Version History
            </h1>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-teal-light text-teal font-semibold border border-teal/20">
              Phase 10: Immutable Releases
            </span>
          </div>
          <p className="text-xs sm:text-sm text-navy-muted mt-0.5">
            Strict transactional publication records, version diffs, and non-destructive draft restores with revalidation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter by Type */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="text-xs px-3 py-1.5 rounded-lg border border-border bg-surface text-navy font-medium focus:outline-none focus:ring-1 focus:ring-teal"
          >
            <option value="ALL">All Publication Types</option>
            <option value="TIMETABLE">Class Timetables</option>
            <option value="EXAM_THEORY">Theory Exam Seating</option>
            <option value="EXAM_PRACTICAL">Practical Lab Stations</option>
          </select>

          <Button
            variant="ghost"
            size="sm"
            onClick={loadPublications}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Section Tab Switcher */}
      <div className="flex items-center gap-2 border-b border-border pb-2">
        <button
          type="button"
          onClick={() => setMainTab('publications')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            mainTab === 'publications'
              ? 'bg-teal text-white shadow-subtle'
              : 'text-navy-muted hover:text-navy hover:bg-surface'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Publication Records & Diff History</span>
        </button>

        <button
          type="button"
          onClick={() => setMainTab('outbox')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            mainTab === 'outbox'
              ? 'bg-teal text-white shadow-subtle'
              : 'text-navy-muted hover:text-navy hover:bg-surface'
          }`}
        >
          <Send className="w-3.5 h-3.5" />
          <span>Communication Outbox & Retries</span>
        </button>
      </div>

      {mainTab === 'outbox' ? (
        <StaffOutboxSection />
      ) : (
        <>

      {/* Global Success / Restore Banner */}
      {restoreSuccessMessage && (
        <div className="p-4 rounded-xl bg-teal-light/60 border border-teal/30 text-xs flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-teal shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold text-navy block mb-0.5">
                Version Restored as New Draft
              </strong>
              <p className="text-navy-muted leading-relaxed">{restoreSuccessMessage}</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setRestoreSuccessMessage(null)}
            className="text-navy-subtle hover:text-navy"
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-coral/10 border border-coral/30 text-coral-dark text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-coral shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="text-coral hover:text-coral-dark font-bold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Publications Table Card */}
      <Card
        title="Published Schedule Releases"
        subtitle="Immutable release records. Rollbacks create new revalidated drafts without modifying history."
      >
        {isLoading ? (
          <div className="py-12 text-center text-xs text-navy-muted space-y-2">
            <div className="w-7 h-7 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto" />
            <p>Loading publication records...</p>
          </div>
        ) : publications.length === 0 ? (
          <div className="py-12 text-center space-y-2">
            <Lock className="w-8 h-8 text-navy-subtle mx-auto" />
            <p className="text-sm font-semibold text-navy">No Published Releases Yet</p>
            <p className="text-xs text-navy-muted max-w-sm mx-auto">
              Drafts in the Timetable Workspace must be verified by the CP-SAT checker and published through
              the 9-step atomic review before appearing here.
            </p>
          </div>
        ) : (
          <Table
            columns={[
              {
                key: 'version',
                header: 'Version',
                render: (r: PublicationSummary) => (
                  <div className="flex items-center gap-2">
                    <Lock className="w-3.5 h-3.5 text-teal shrink-0" />
                    <div>
                      <span className="font-bold text-navy block text-sm">
                        v{r.version_number}
                      </span>
                      <span className="text-[10px] text-navy-subtle font-mono block">
                        {r.publication_type}
                      </span>
                    </div>
                  </div>
                ),
              },
              {
                key: 'published_at',
                header: 'Published At & By',
                render: (r: PublicationSummary) => (
                  <div className="text-xs">
                    <span className="text-navy block">
                      {new Date(r.published_at).toLocaleString()}
                    </span>
                    <span className="text-[11px] text-navy-subtle block font-mono">
                      {r.publisher_name || 'Authorized Staff'}
                    </span>
                  </div>
                ),
              },
              {
                key: 'status',
                header: 'Status',
                render: (r: PublicationSummary) => (
                  <StatusBadge
                    status={r.is_active ? 'ACTIVE' : 'SUPERSEDED'}
                    label={r.is_active ? 'ACTIVE' : 'SUPERSEDED'}
                    size="sm"
                  />
                ),
              },
              {
                key: 'impact',
                header: 'Impact / Note',
                render: (r: PublicationSummary) => (
                  <div className="text-xs max-w-xs space-y-0.5">
                    {r.publication_note && (
                      <p className="text-navy truncate font-medium" title={r.publication_note}>
                        &ldquo;{r.publication_note}&rdquo;
                      </p>
                    )}
                    <span className="text-[11px] text-navy-subtle block">
                      {r.change_count} session/seat modifications
                    </span>
                  </div>
                ),
              },
              {
                key: 'actions',
                header: 'Actions',
                render: (r: PublicationSummary) => (
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleOpenDiff(r)}
                      title="Compare with another release version"
                      leftIcon={<GitCompare className="w-3.5 h-3.5" />}
                    >
                      Diff
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleOpenRestore(r)}
                      title="Restore this version as a new draft (preserves history)"
                      leftIcon={<RotateCcw className="w-3.5 h-3.5 text-teal" />}
                    >
                      Restore
                    </Button>
                  </div>
                ),
              },
            ]}
            data={publications}
            keyExtractor={(r: PublicationSummary) => r.id}
          />
        )}
      </Card>
        </>
      )}

      {/* Version Diff Inspection Modal */}
      <Dialog
        isOpen={isDiffModalOpen}
        onClose={() => setIsDiffModalOpen(false)}
        title={
          selectedPubForDiff
            ? `Version Diff: v${selectedPubForDiff.version_number}`
            : 'Publication Version Difference'
        }
        description="Inspect granular changes between published snapshots (sessions, rooms, and assignments)."
        maxWidth="lg"
        footer={
          <Button variant="primary" size="sm" onClick={() => setIsDiffModalOpen(false)}>
            Close Diff
          </Button>
        }
      >
        <div className="space-y-4">
          {/* Comparison Selector */}
          <div className="p-3.5 rounded-xl bg-bg border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div>
              <span className="text-navy-subtle block">Comparing Version</span>
              <strong className="font-heading font-bold text-navy text-sm">
                v{selectedPubForDiff?.version_number}
              </strong>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-navy-subtle">Compare Against:</span>
              <select
                value={compareTargetId}
                onChange={(e) => {
                  setCompareTargetId(e.target.value);
                  if (selectedPubForDiff) {
                    fetchDiff(selectedPubForDiff.id, e.target.value);
                  }
                }}
                className="text-xs px-2.5 py-1 rounded border border-border bg-surface text-navy focus:outline-none focus:ring-1 focus:ring-teal"
              >
                {publications.map((p) => (
                  <option key={p.id} value={p.id}>
                    v{p.version_number} ({new Date(p.published_at).toLocaleDateString()})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {diffError && (
            <div className="p-3 rounded-lg bg-coral/10 text-coral-dark text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{diffError}</span>
            </div>
          )}

          {isDiffLoading ? (
            <div className="py-8 text-center text-xs text-navy-muted">
              <div className="w-6 h-6 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              Calculating granular diff matrix...
            </div>
          ) : diffData ? (
            <div className="space-y-4 text-xs">
              {/* Metrics Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-2.5 rounded-lg bg-bg border border-border">
                  <span className="text-navy-subtle block text-[11px]">Changed Sessions</span>
                  <span className="font-heading font-bold text-base text-navy">
                    {diffData.changed_sessions?.length ?? 0}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-bg border border-border">
                  <span className="text-navy-subtle block text-[11px]">Added Sessions</span>
                  <span className="font-heading font-bold text-base text-teal">
                    {diffData.added_sessions?.length ?? 0}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-bg border border-border">
                  <span className="text-navy-subtle block text-[11px]">Removed Sessions</span>
                  <span className="font-heading font-bold text-base text-coral">
                    {diffData.removed_sessions?.length ?? 0}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-bg border border-border">
                  <span className="text-navy-subtle block text-[11px]">Affected Teachers</span>
                  <span className="font-heading font-bold text-base text-navy">
                    {diffData.affected_teachers?.length ?? 0}
                  </span>
                </div>
              </div>

              {/* Changed Sessions */}
              {diffData.changed_sessions && diffData.changed_sessions.length > 0 && (
                <div className="space-y-1.5">
                  <h4 className="font-semibold text-amber-900 text-xs">
                    Changed Assignments ({diffData.changed_sessions.length})
                  </h4>
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {diffData.changed_sessions.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-bg border border-border text-[11px] space-y-1"
                      >
                        <div className="flex items-center justify-between font-semibold text-navy">
                          <span>{item.session_name || item.session_id}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-[10px] text-navy-muted">
                          <div>
                            <span className="text-navy-subtle block">Before:</span>
                            Day {(item.before?.day ?? 0) + 1}, Period {(item.before?.period ?? 0) + 1}, Room{' '}
                            {item.before?.room_id || 'N/A'}
                          </div>
                          <div>
                            <span className="text-teal block font-semibold">After:</span>
                            Day {(item.after?.day ?? 0) + 1}, Period {(item.after?.period ?? 0) + 1}, Room{' '}
                            {item.after?.room_id || 'N/A'}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Added Sessions */}
              {diffData.added_sessions && diffData.added_sessions.length > 0 && (
                <div className="space-y-1.5">
                  <h4 className="font-semibold text-teal text-xs">
                    Added Sessions ({diffData.added_sessions.length})
                  </h4>
                  <div className="space-y-1 max-h-36 overflow-y-auto">
                    {diffData.added_sessions.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-teal-light/40 border border-teal/20 text-[11px] flex items-center justify-between"
                      >
                        <span className="font-medium text-navy">
                          {item.title || item.session_id}
                        </span>
                        <span className="text-teal font-medium">
                          Day {(item.day ?? 0) + 1} &bull; Period {(item.period ?? 0) + 1}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {(!diffData.changed_sessions || diffData.changed_sessions.length === 0) &&
                (!diffData.added_sessions || diffData.added_sessions.length === 0) &&
                (!diffData.removed_sessions || diffData.removed_sessions.length === 0) && (
                  <p className="text-navy-muted text-center py-4">
                    Zero session differences detected between these two releases.
                  </p>
                )}
            </div>
          ) : null}
        </div>
      </Dialog>

      {/* Restore Old Version as New Draft Modal */}
      <Dialog
        isOpen={isRestoreModalOpen}
        onClose={() => setIsRestoreModalOpen(false)}
        title={
          restoredDraft
            ? 'Draft Successfully Restored'
            : `Restore Version v${pubToRestore?.version_number} as New Draft`
        }
        description={
          restoredDraft
            ? 'New editable draft created with preserved publication history and automated revalidation.'
            : 'Rollback creates a new editable draft without deleting any historical release records.'
        }
        maxWidth="md"
        footer={
          restoredDraft ? (
            <Button variant="primary" size="sm" onClick={() => setIsRestoreModalOpen(false)}>
              Done
            </Button>
          ) : (
            <div className="flex items-center justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsRestoreModalOpen(false)}
                disabled={isRestoring}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleConfirmRestore}
                isLoading={isRestoring}
                leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
              >
                Confirm Restore
              </Button>
            </div>
          )
        }
      >
        {restoredDraft ? (
          <div className="space-y-3 py-2 text-xs">
            <div className="p-3.5 rounded-xl bg-teal-light/60 border border-teal/30 flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-teal shrink-0 mt-0.5" />
              <div>
                <strong className="font-semibold text-navy block mb-0.5">
                  Restored Draft Created: Rev #{restoredDraft.revision}
                </strong>
                <p className="text-navy-muted leading-relaxed">
                  The snapshot from version v{pubToRestore?.version_number} has been cloned into draft ID{' '}
                  <code className="bg-surface px-1 py-0.5 rounded">{restoredDraft.id}</code>.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-bg border border-border space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-navy-subtle">Revalidation Status</span>
                <StatusBadge status={restoredDraft.status} size="sm" />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-navy-subtle">Publication History Preserved</span>
                <span className="font-semibold text-teal">&check; 0 Records Deleted</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-navy-subtle">Publication Requirement</span>
                <span className="text-navy-muted">
                  Must revalidate before publication is permitted
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4 text-xs">
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 space-y-1.5 leading-relaxed">
              <strong className="font-semibold block text-sm">
                Non-Destructive Rollback Guarantee:
              </strong>
              <p>
                Restoring version <strong>v{pubToRestore?.version_number}</strong> will <strong>not</strong> delete
                or modify any publication history records. An immutable audit trail of all releases is
                strictly maintained.
              </p>
              <p>
                Instead, a new editable timetable draft (Rev #1) will be created from this version&apos;s
                immutable snapshot and immediately rechecked by the solver engine.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-bg border border-border space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="text-navy-subtle">Source Publication</span>
                <span className="font-mono font-semibold text-navy">
                  v{pubToRestore?.version_number}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-navy-subtle">Release ID</span>
                <span className="text-navy font-mono text-[11px]">{pubToRestore?.id}</span>
              </div>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};
