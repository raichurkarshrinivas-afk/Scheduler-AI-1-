import React, { useState, useEffect, useCallback } from 'react';
import {
  PlusCircle,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Send,
  RefreshCw,
} from 'lucide-react';
import { Card } from '../../components/common/Card';
import { Table } from '../../components/common/Table';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Button } from '../../components/common/Button';
import { FormField, Input, Select, Textarea } from '../../components/common/FormField';
import { Dialog } from '../../components/common/Dialog';
import { api } from '../../services/api';
import {
  AuthenticatedFeedbackCategory,
  FeedbackStatus,
  UserSubmittedFeedback,
} from '../../types';

export const StudentFeedback: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'submit' | 'history'>('submit');

  // Submit form state
  const [category, setCategory] = useState<AuthenticatedFeedbackCategory>('SUGGESTION');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [pageReference, setPageReference] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<{
    referenceCode: string;
    message: string;
  } | null>(null);

  // Submissions history state
  const [submissions, setSubmissions] = useState<UserSubmittedFeedback[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    setIsLoadingHistory(true);
    setHistoryError(null);
    try {
      const data = await api.feedback.getMySubmissions();
      setSubmissions(data);
    } catch (err: any) {
      setHistoryError(err.message || 'Unable to load your past feedback.');
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab, fetchHistory]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (subject.trim().length < 3) {
      setSubmitError('Subject must be at least 3 characters.');
      return;
    }
    if (message.trim().length < 10) {
      setSubmitError('Message must be at least 10 characters.');
      return;
    }
    if (message.length > 5000) {
      setSubmitError('Message cannot exceed 5,000 characters.');
      return;
    }

    setIsSubmitting(true);
    try {
      const resp = await api.feedback.submitAuthenticated({
        category,
        subject: subject.trim(),
        message: message.trim(),
        page_reference: pageReference.trim() || undefined,
      });

      setSubmitSuccess({
        referenceCode: resp.reference_code,
        message: resp.message,
      });

      setSubject('');
      setMessage('');
      setPageReference('');
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to submit feedback.');
    } finally {
      setIsSubmitting(false);
    }
  };
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
            Student Feedback & Assistance
          </h1>
          <p className="text-xs sm:text-sm text-navy-muted">
            Submit technical observations, app suggestions, or accessibility feedback to your institution administrators.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-1.5 p-1 bg-surface border border-border rounded-xl">
          <button
            type="button"
            onClick={() => setActiveTab('submit')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'submit'
                ? 'bg-teal text-white shadow-subtle'
                : 'text-navy-muted hover:text-navy hover:bg-bg'
            }`}
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Feedback</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('history')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'history'
                ? 'bg-teal text-white shadow-subtle'
                : 'text-navy-muted hover:text-navy hover:bg-bg'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>My Submitted Feedback ({submissions.length})</span>
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: SUBMIT FEEDBACK */}
      {/* ========================================================================= */}
      {activeTab === 'submit' && (
        <Card className="max-w-2xl mx-auto bg-white shadow-sm p-6">
          {/* Explicit Policy Warning Notice */}
          <div className="mb-5 p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <strong className="block font-semibold text-amber-800 text-sm mb-0.5">
                Important: Feedback is NOT a Timetable Change Request
              </strong>
              <p className="leading-relaxed">
                This channel is strictly for system bug reports, facility accessibility feedback, or platform suggestions. It is <strong>NOT</strong> an official course enrollment, batch swap, or timetable-change petition. For official timetable changes, please contact your department academic coordinator or faculty advisor directly.
              </p>
            </div>
          </div>

          {submitError && (
            <div className="mb-4 p-3 rounded-lg bg-coral-light/60 border border-coral/30 text-xs text-coral font-medium" role="alert">
              {submitError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <FormField label="Category" htmlFor="student-feedback-cat" required>
              <Select
                id="student-feedback-cat"
                value={category}
                onChange={(e) => setCategory(e.target.value as AuthenticatedFeedbackCategory)}
                required
              >
                <option value="SUGGESTION">General Suggestion</option>
                <option value="BUG_REPORT">Technical Bug / Application Issue</option>
                <option value="ACCESS_ISSUE">Accessibility / Facility Mobility Issue</option>
                <option value="SCHEDULING_ISSUE">Scheduling Conflict Observation</option>
                <option value="OTHER">Other Inquiry</option>
              </Select>
            </FormField>

            <FormField
              label="Related Page or Resource (Optional)"
              htmlFor="student-page-ref"
              helperText="e.g. Timetable Grid -> Room 204, or Exam Hall B -> Seat 14"
            >
              <Input
                id="student-page-ref"
                placeholder="e.g. Exams & Seats -> Main Auditorium"
                value={pageReference}
                onChange={(e) => setPageReference(e.target.value)}
                maxLength={255}
              />
            </FormField>

            <FormField
              label="Subject"
              htmlFor="student-subj"
              required
              helperText={`${subject.length}/200 characters`}
            >
              <Input
                id="student-subj"
                placeholder="Brief summary of your feedback"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                maxLength={200}
                required
              />
            </FormField>

            <FormField
              label="Feedback Details"
              htmlFor="student-msg"
              required
              helperText={`${message.length}/5000 characters (min 10 characters)`}
            >
              <Textarea
                id="student-msg"
                rows={5}
                placeholder="Describe what you observed, what can be improved, or accessibility needs..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                maxLength={5000}
                required
              />
            </FormField>

            <div className="p-3 rounded-lg bg-bg border border-border/70 text-[11px] text-navy-subtle flex items-start gap-2">
              <Lock className="w-3.5 h-3.5 text-navy-subtle shrink-0 mt-0.5" />
              <span>
                Your student profile and institution are safely derived from your authenticated session. Account credentials, session tokens, and confidential student records are never automatically scraped or recorded.
              </span>
            </div>

            <div className="pt-2 flex justify-end">
              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={isSubmitting}
                className="flex items-center gap-2"
              >
                <Send className="w-4 h-4" />
                <span>Submit Feedback</span>
              </Button>
            </div>
          </form>

          {/* Persistence Confirmation Modal */}
          <Dialog
            isOpen={!!submitSuccess}
            onClose={() => setSubmitSuccess(null)}
            title="Feedback Persisted Successfully"
            footer={
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setSubmitSuccess(null);
                  setActiveTab('history');
                }}
              >
                View in My Submissions
              </Button>
            }
          >
            <div className="space-y-4 text-xs">
              <div className="flex items-start gap-3 p-3.5 bg-teal-light/50 border border-teal/20 rounded-xl">
                <CheckCircle2 className="w-6 h-6 text-teal shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-teal-dark text-sm mb-1">
                    {submitSuccess?.message || 'Feedback logged securely.'}
                  </p>
                  <p className="text-navy-muted leading-relaxed">
                    Your feedback has been saved to the institutional database and assigned for administrator review.
                  </p>
                </div>
              </div>

              <div className="p-3.5 bg-surface border border-border rounded-xl space-y-1.5">
                <span className="text-[11px] uppercase tracking-wider text-navy-subtle font-semibold block">
                  Submission Reference Code:
                </span>
                <div className="font-mono font-bold text-base text-navy tracking-wider select-all bg-white px-3 py-1.5 rounded border border-border/80 inline-block">
                  {submitSuccess?.referenceCode}
                </div>
              </div>
            </div>
          </Dialog>
        </Card>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: HISTORY (MY SUBMISSIONS) */}
      {/* ========================================================================= */}
      {activeTab === 'history' && (
        <Card className="bg-white overflow-hidden p-0">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <div>
              <h2 className="font-heading text-sm font-bold text-navy">
                My Submitted Feedback
              </h2>
              <p className="text-xs text-navy-muted">
                View the lifecycle status of your submissions. Internal reviewer deliberations remain confidential.
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchHistory}
              isLoading={isLoadingHistory}
              className="flex items-center gap-1.5 text-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </Button>
          </div>

          {historyError && (
            <div className="m-4 p-3 rounded-lg bg-coral-light/60 border border-coral/30 text-xs text-coral">
              {historyError}
            </div>
          )}

          <Table
            columns={[
              {
                key: 'reference_code',
                header: 'Ref Code',
                render: (item: UserSubmittedFeedback) => (
                  <span className="font-mono text-xs font-bold text-navy select-all">
                    {item.reference_code}
                  </span>
                ),
              },
              {
                key: 'category',
                header: 'Category',
                render: (item: UserSubmittedFeedback) => (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-bg border border-border text-navy-muted">
                    {item.category.replace('_', ' ')}
                  </span>
                ),
              },
              {
                key: 'subject',
                header: 'Subject & Note',
                render: (item: UserSubmittedFeedback) => (
                  <div className="max-w-md">
                    <div className="font-semibold text-navy text-xs">{item.subject}</div>
                    <div className="text-xs text-navy-muted line-clamp-2 mt-0.5">
                      {item.message}
                    </div>
                    {item.page_reference && (
                      <div className="text-[10px] text-teal font-mono mt-1">
                        Ref: {item.page_reference}
                      </div>
                    )}
                  </div>
                ),
              },
              {
                key: 'status',
                header: 'Review Status',
                render: (item: UserSubmittedFeedback) => {
                  const statusColors: Record<FeedbackStatus, 'ACTIVE' | 'WARNING' | 'ALERT' | 'INFO' | 'PENDING'> = {
                    new: 'ALERT',
                    reviewing: 'WARNING',
                    awaiting_information: 'INFO',
                    resolved: 'ACTIVE',
                    closed: 'PENDING',
                  };
                  return <StatusBadge status={statusColors[item.status]} label={item.status.toUpperCase()} size="sm" />;
                },
              },
              {
                key: 'created_at',
                header: 'Submitted',
                render: (item: UserSubmittedFeedback) => (
                  <span className="text-[11px] text-navy-subtle">
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                ),
              },
            ]}
            data={submissions}
            keyExtractor={(item) => item.id}
          />

          {submissions.length === 0 && !isLoadingHistory && (
            <div className="p-8 text-center text-xs text-navy-muted space-y-2">
              <p>You have not logged any feedback inquiries yet.</p>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setActiveTab('submit')}
                className="mt-2"
              >
                Submit Feedback
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};
