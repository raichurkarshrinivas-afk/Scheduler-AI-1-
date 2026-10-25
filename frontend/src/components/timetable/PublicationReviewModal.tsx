import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  Lock,
  Send,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { Dialog } from '../common/Dialog';
import { Button } from '../common/Button';
import { StatusBadge } from '../common/StatusBadge';
import { api } from '../../services/api';
import { PrePublishReview, Publication } from '../../types';

export interface PublicationReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  draftId: string;
  expectedRevision: number;
  termId?: string;
  termName?: string;
  onPublished?: (pub: Publication) => void;
}

export const PublicationReviewModal: React.FC<PublicationReviewModalProps> = ({
  isOpen,
  onClose,
  draftId,
  expectedRevision,
  termName,
  onPublished,
}) => {
  const [review, setReview] = useState<PrePublishReview | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [publicationNote, setPublicationNote] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [publishedRecord, setPublishedRecord] = useState<Publication | null>(null);

  // Fetch pre-publish review when modal opens
  useEffect(() => {
    if (isOpen && draftId) {
      setPublishedRecord(null);
      setErrorMessage(null);
      setIsLoading(true);
      api.publications
        .getPrePublishReview(draftId)
        .then((data) => {
          setReview(data);
          if (!publicationNote) {
            setPublicationNote(
              `Official publication of ${termName || 'Academic Term'} timetable (Rev #${data.revision})`
            );
          }
        })
        .catch((err) => {
          setErrorMessage(err.message || 'Failed to load pre-publish review.');
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [isOpen, draftId, termName]);

  const handlePublish = async () => {
    if (!draftId) return;
    setIsPublishing(true);
    setErrorMessage(null);

    try {
      const pub = await api.publications.publish({
        draft_id: draftId,
        publication_type: 'TIMETABLE',
        expected_revision: expectedRevision,
        publication_note: publicationNote.trim() || undefined,
      });

      setPublishedRecord(pub);
      if (onPublished) {
        onPublished(pub);
      }
    } catch (err: any) {
      if (err.status === 409) {
        setErrorMessage(
          err.message ||
            'Publication Conflict (409): The draft revision is stale or a competing publication holds active reservations.'
        );
      } else {
        setErrorMessage(err.message || 'Publication transaction failed.');
      }
    } finally {
      setIsPublishing(false);
    }
  };

  const isCheckerPassed = review?.validation_report?.is_valid ?? false;
  const hasReservationConflicts =
    (review?.potential_reservation_conflicts &&
      review.potential_reservation_conflicts.length > 0) ||
    false;
  const canPublish =
    (review?.can_publish ?? false) && !isLoading && !isPublishing && !publishedRecord;

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={publishedRecord ? 'Schedule Published Successfully' : 'Controlled Publication Review'}
      description={
        publishedRecord
          ? 'Transactionally committed immutable release with audit checksum.'
          : 'Strict 9-step atomic verification before immutable student and teacher release.'
      }
      maxWidth="lg"
      footer={
        publishedRecord ? (
          <Button variant="primary" size="sm" onClick={onClose}>
            Done
          </Button>
        ) : (
          <div className="flex items-center justify-between w-full">
            <span className="text-[11px] text-navy-subtle">
              Zero external services invoked inside the DB transaction.
            </span>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={onClose} disabled={isPublishing}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handlePublish}
                disabled={!canPublish}
                isLoading={isPublishing}
                leftIcon={<Lock className="w-3.5 h-3.5" />}
              >
                Authorise & Publish
              </Button>
            </div>
          </div>
        )
      }
    >
      {publishedRecord ? (
        <div className="space-y-4 py-2">
          <div className="p-4 rounded-xl bg-teal-light/60 border border-teal/30 flex items-start gap-3">
            <CheckCircle2 className="w-6 h-6 text-teal shrink-0 mt-0.5" />
            <div>
              <h4 className="font-heading font-bold text-navy text-sm">
                Official Release v{publishedRecord.version_number} Committed
              </h4>
              <p className="text-xs text-navy-muted mt-1 leading-relaxed">
                The timetable is now published. Active shared-resource reservations have been updated
                and student timetable views now reflect this official version.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-bg border border-border space-y-2.5 text-xs">
            <div className="flex justify-between items-center py-1 border-b border-border">
              <span className="text-navy-subtle">Publication ID</span>
              <span className="font-mono text-navy font-semibold">{publishedRecord.id}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-border">
              <span className="text-navy-subtle">Release Version</span>
              <span className="font-semibold text-teal">v{publishedRecord.version_number}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-border">
              <span className="text-navy-subtle">Committed Timestamp</span>
              <span className="text-navy">{new Date(publishedRecord.published_at).toUTCString()}</span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-navy-subtle">Communication Outbox</span>
              <span className="text-teal font-medium flex items-center gap-1">
                <Send className="w-3 h-3" /> Notifications Enqueued
              </span>
            </div>
          </div>
        </div>
      ) : isLoading ? (
        <div className="py-12 text-center space-y-3">
          <div className="w-8 h-8 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-navy-muted">
            Executing independent checker verification & locking publication scope...
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Error Banner */}
          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-coral/10 border border-coral/30 text-coral-dark text-xs flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-coral shrink-0 mt-0.5" />
              <div>
                <strong className="font-semibold block mb-0.5">Publication Blocked</strong>
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          {/* Checker Result Card */}
          <div className="p-4 rounded-xl bg-surface border border-border space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck
                  className={`w-5 h-5 ${isCheckerPassed ? 'text-teal' : 'text-coral'}`}
                />
                <h4 className="font-heading font-semibold text-sm text-navy">
                  Step 5: Independent Schedule Verification
                </h4>
              </div>
              <StatusBadge
                status={isCheckerPassed ? 'PUBLISHED' : 'INVALID'}
                label={isCheckerPassed ? 'CHECKER PASSED' : 'CHECKER FAILED'}
                size="sm"
              />
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
              <div className="p-2.5 rounded-lg bg-bg border border-border">
                <span className="text-navy-subtle block text-[11px]">Hard Violations</span>
                <span
                  className={`font-heading font-bold text-base ${
                    (review?.validation_report?.violations?.length ?? 0) === 0
                      ? 'text-teal'
                      : 'text-coral'
                  }`}
                >
                  {review?.validation_report?.violations?.length ?? 0}
                </span>
              </div>

              <div className="p-2.5 rounded-lg bg-bg border border-border">
                <span className="text-navy-subtle block text-[11px]">Expected Revision</span>
                <span className="font-mono font-semibold text-navy text-sm">
                  Rev #{expectedRevision}
                </span>
              </div>

              <div className="p-2.5 rounded-lg bg-bg border border-border">
                <span className="text-navy-subtle block text-[11px]">Rule Set Version</span>
                <span className="text-navy-muted font-medium text-xs">
                  {review?.validation_report?.checker_version || 'v1.0.0'}
                </span>
              </div>

              <div className="p-2.5 rounded-lg bg-bg border border-border">
                <span className="text-navy-subtle block text-[11px]">Unmet Preferences</span>
                <span className="font-semibold text-navy text-sm">
                  {review?.unmet_preferences_count ?? 0}
                </span>
              </div>
            </div>

            {review?.validation_report?.violations &&
              review.validation_report.violations.length > 0 && (
                <div className="p-2.5 rounded-lg bg-coral/10 border border-coral/20 text-coral-dark text-xs space-y-1">
                  <strong className="block text-[11px]">Detected Rule Violations:</strong>
                  {review.validation_report.violations.map((v, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-[11px]">
                      <span className="font-mono font-bold">&bull; [{v.code || 'VIOLATION'}]</span>
                      <span>{v.message}</span>
                    </div>
                  ))}
                </div>
              )}
          </div>

          {/* Shared-Resource Reservations Check */}
          <div className="p-3.5 rounded-xl bg-bg border border-border text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-teal" />
              <div>
                <span className="font-medium text-navy block">
                  Step 4: Active Shared-Resource Reservation Check
                </span>
                <span className="text-navy-subtle text-[11px]">
                  Guarantees no two competing publications double-book rooms, halls, or lab workstations.
                </span>
              </div>
            </div>
            {hasReservationConflicts ? (
              <span className="font-bold text-coral flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> Conflict Detected
              </span>
            ) : (
              <span className="font-semibold text-teal flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> 0 Collisions
              </span>
            )}
          </div>

          {/* Scope & Impact Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-surface border border-border">
              <span className="text-navy-subtle block mb-1">Changed Sessions</span>
              <span className="font-heading font-bold text-lg text-navy">
                {review?.changed_sessions_count ?? 0}
              </span>
              <span className="text-[11px] text-navy-muted block mt-0.5">
                {review?.previous_active_version
                  ? `Diff vs v${review.previous_active_version}`
                  : 'Initial publication release'}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-surface border border-border">
              <span className="text-navy-subtle block mb-1">Affected Faculty</span>
              <span className="font-heading font-bold text-lg text-teal">
                {review?.affected_teachers_count ?? 0}
              </span>
              <span className="text-[11px] text-navy-muted block mt-0.5">
                Teaching assignments updated
              </span>
            </div>

            <div className="p-3 rounded-lg bg-surface border border-border">
              <span className="text-navy-subtle block mb-1">Affected Students</span>
              <span className="font-heading font-bold text-lg text-navy">
                {review?.affected_students_count ?? 0}
              </span>
              <span className="text-[11px] text-navy-muted block mt-0.5">
                Enrolled cohort timetable views
              </span>
            </div>
          </div>

          {/* Warnings (if any) */}
          {review?.warnings && review.warnings.length > 0 && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs space-y-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-amber-900">
                <Info className="w-4 h-4 text-amber-700" />
                <span>Documented Warnings ({review.warnings.length})</span>
              </div>
              <ul className="list-disc pl-5 space-y-1 text-amber-800 text-[11px]">
                {review.warnings.map((w, idx) => (
                  <li key={idx}>
                    {w.message || JSON.stringify(w)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Step 8: Communication Outbox Events */}
          <div className="p-3.5 rounded-xl bg-surface border border-border flex items-start gap-2.5 text-xs">
            <Send className="w-4 h-4 text-teal shrink-0 mt-0.5" />
            <div>
              <span className="font-medium text-navy block">
                Step 8: Transactional Communication Outbox
              </span>
              <p className="text-navy-subtle text-[11px] mt-0.5 leading-relaxed">
                Events will be written atomically to the internal outbox table during commit. No external
                APIs are called inside the transaction boundary.
              </p>
            </div>
          </div>

          {/* Publication Note */}
          <div className="space-y-1.5">
            <label htmlFor="pub-note" className="block text-xs font-semibold text-navy">
              Audit Publication Note <span className="text-coral">*</span>
            </label>
            <textarea
              id="pub-note"
              rows={2}
              value={publicationNote}
              onChange={(e) => setPublicationNote(e.target.value)}
              placeholder="E.g. Official Autumn 2026 Timetable Release after room availability review."
              className="w-full px-3 py-2 text-xs rounded-lg border border-border bg-bg text-navy focus:outline-none focus:ring-1 focus:ring-teal"
            />
            <span className="text-[11px] text-navy-subtle block">
              This note is permanently recorded in the immutable audit log and visible on student notice boards.
            </span>
          </div>
        </div>
      )}
    </Dialog>
  );
};
