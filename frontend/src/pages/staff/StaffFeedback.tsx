import React, { useState, useEffect, useCallback } from 'react';
import {
  MessageSquare,
  Search,
  Filter,
  RefreshCw,
  PlusCircle,
  Eye,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Shield,
  User,
  Send,
} from 'lucide-react';
import { Card } from '../../components/common/Card';
import { Table } from '../../components/common/Table';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Button } from '../../components/common/Button';
import { FormField, Input, Select, Textarea } from '../../components/common/FormField';
import { Dialog } from '../../components/common/Dialog';
import { api } from '../../services/api';
import {
  FeedbackManageItem,
  FeedbackDetailItem,
  FeedbackStatus,
  AuthenticatedFeedbackCategory,
  UserSubmittedFeedback,
} from '../../types';

export const StaffFeedback: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'triage' | 'submit' | 'my-submissions'>('triage');

  // Triage state
  const [items, setItems] = useState<FeedbackManageItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [includePublic] = useState<boolean>(true);

  // Selected item detail
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detailItem, setDetailItem] = useState<FeedbackDetailItem | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [newNote, setNewNote] = useState('');
  const [isAddingNote, setIsAddingNote] = useState(false);
  const [selectedNewStatus, setSelectedNewStatus] = useState<FeedbackStatus>('reviewing');
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  // Authenticated submit form state
  const [submitCategory, setSubmitCategory] = useState<AuthenticatedFeedbackCategory>('BUG_REPORT');
  const [submitSubject, setSubmitSubject] = useState('');
  const [submitMessage, setSubmitMessage] = useState('');
  const [submitPageRef, setSubmitPageRef] = useState('');
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<{ referenceCode: string; message: string } | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // My submissions state
  const [mySubmissions, setMySubmissions] = useState<UserSubmittedFeedback[]>([]);
  const [isMySubmissionsLoading, setIsMySubmissionsLoading] = useState(false);

  // Fetch manage list
  const fetchTriageList = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const resp = await api.feedback.getManageList({
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        search: searchQuery.trim() || undefined,
        include_public: includePublic,
        limit: 50,
        offset: 0,
      });
      setItems(resp.items);
      setTotalCount(resp.total);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load feedback inquiries.');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, categoryFilter, searchQuery, includePublic]);

  // Fetch detail
  const fetchDetail = async (id: string) => {
    setSelectedId(id);
    setIsDetailLoading(true);
    try {
      const detail = await api.feedback.getManageDetail(id);
      setDetailItem(detail);
      setSelectedNewStatus(detail.status);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load feedback details.');
    } finally {
      setIsDetailLoading(false);
    }
  };

  // Fetch my submissions
  const fetchMySubmissions = useCallback(async () => {
    setIsMySubmissionsLoading(true);
    try {
      const subs = await api.feedback.getMySubmissions();
      setMySubmissions(subs);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load your submissions.');
    } finally {
      setIsMySubmissionsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'triage') {
      fetchTriageList();
    } else if (activeTab === 'my-submissions') {
      fetchMySubmissions();
    }
  }, [activeTab, fetchTriageList, fetchMySubmissions]);

  // Handle status update
  const handleStatusUpdate = async () => {
    if (!selectedId || !detailItem) return;
    setIsUpdatingStatus(true);
    try {
      await api.feedback.updateStatus(selectedId, {
        status: selectedNewStatus,
        internal_note: newNote.trim() ? newNote.trim() : undefined,
      });
      if (newNote.trim()) {
        setNewNote('');
      }
      await fetchDetail(selectedId);
      await fetchTriageList();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update feedback status.');
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  // Handle add internal note
  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId || !newNote.trim()) return;
    setIsAddingNote(true);
    try {
      await api.feedback.addInternalNote(selectedId, newNote.trim());
      setNewNote('');
      await fetchDetail(selectedId);
      await fetchTriageList();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to add internal note.');
    } finally {
      setIsAddingNote(false);
    }
  };

  // Handle staff feedback submit
  const handleAuthenticatedSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (submitSubject.trim().length < 3) {
      setSubmitError('Subject must be at least 3 characters.');
      return;
    }
    if (submitMessage.trim().length < 10) {
      setSubmitError('Message must be at least 10 characters.');
      return;
    }
    if (submitMessage.length > 5000) {
      setSubmitError('Message cannot exceed 5000 characters.');
      return;
    }

    setIsSubmittingFeedback(true);
    try {
      const resp = await api.feedback.submitAuthenticated({
        category: submitCategory,
        subject: submitSubject.trim(),
        message: submitMessage.trim(),
        page_reference: submitPageRef.trim() || undefined,
      });

      setSubmitSuccess({
        referenceCode: resp.reference_code,
        message: resp.message,
      });

      setSubmitSubject('');
      setSubmitMessage('');
      setSubmitPageRef('');
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to submit feedback.');
    } finally {
      setIsSubmittingFeedback(false);
    }
  };
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
            Feedback & Contact Center
          </h1>
          <p className="text-xs sm:text-sm text-navy-muted">
            Triage operational feedback, investigate bug reports, review public inquiries, and manage internal reviewer notes.
          </p>
        </div>

        <div className="flex items-center gap-1.5 p-1 bg-surface border border-border rounded-xl">
          <button
            type="button"
            onClick={() => setActiveTab('triage')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'triage'
                ? 'bg-teal text-white shadow-subtle'
                : 'text-navy-muted hover:text-navy hover:bg-bg'
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            <span>Triage Queue ({totalCount})</span>
          </button>

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
            <span>Submit Feedback</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('my-submissions')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'my-submissions'
                ? 'bg-teal text-white shadow-subtle'
                : 'text-navy-muted hover:text-navy hover:bg-bg'
            }`}
          >
            <User className="w-3.5 h-3.5" />
            <span>My Submissions</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3.5 rounded-lg bg-coral-light/60 border border-coral/30 text-xs text-coral font-medium flex items-start gap-2" role="alert">
          <AlertTriangle className="w-4 h-4 text-coral shrink-0 mt-0.5" />
          <div className="flex-1">{errorMsg}</div>
          <button type="button" onClick={() => setErrorMsg(null)} className="text-coral hover:underline font-bold">
            Dismiss
          </button>
        </div>
      )}

      {activeTab === 'triage' && (
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-ice-light border border-ice/30 text-xs text-navy flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-ice shrink-0" />
              <span>
                <strong>Controlled Scoped Visibility & Inert Content:</strong> Submissions are strictly isolated by institution. All messages and notes are rendered as untrusted plaintext to neutralize script execution.
              </span>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchTriageList}
              isLoading={isLoading}
              className="flex items-center gap-1 shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </Button>
          </div>

          <Card className="p-4 bg-white">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-navy uppercase tracking-wider mb-1">
                  Search
                </label>
                <div className="relative">
                  <Search className="w-4 h-4 text-navy-subtle absolute left-3 top-2.5" />
                  <Input
                    placeholder="Search ref, subject..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 text-xs"
                    onKeyDown={(e) => e.key === 'Enter' && fetchTriageList()}
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-navy uppercase tracking-wider mb-1">
                  Category
                </label>
                <Select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="text-xs"
                >
                  <option value="">All Categories</option>
                  <option value="BUG_REPORT">Bug Report</option>
                  <option value="SUGGESTION">Suggestion</option>
                  <option value="ACCESS_ISSUE">Access Issue</option>
                  <option value="SCHEDULING_ISSUE">Scheduling Issue</option>
                  <option value="GENERAL_INQUIRY">General Inquiry</option>
                  <option value="PILOT_REQUEST">Pilot Request</option>
                  <option value="ACCESSIBILITY">Accessibility</option>
                  <option value="OTHER">Other</option>
                </Select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-navy uppercase tracking-wider mb-1">
                  Status
                </label>
                <Select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="text-xs"
                >
                  <option value="">All Statuses</option>
                  <option value="new">New</option>
                  <option value="reviewing">Reviewing</option>
                  <option value="awaiting_information">Awaiting Information</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </Select>
              </div>

              <div className="flex items-end gap-2">
                <Button
                  variant="primary"
                  size="md"
                  onClick={fetchTriageList}
                  isLoading={isLoading}
                  className="w-full text-xs flex items-center justify-center gap-1.5"
                >
                  <Filter className="w-3.5 h-3.5" />
                  <span>Apply Filters</span>
                </Button>
              </div>
            </div>
          </Card>

          <Card className="bg-white overflow-hidden p-0">
            <Table
              columns={[
                {
                  key: 'reference_code',
                  header: 'Ref Code',
                  render: (item: FeedbackManageItem) => (
                    <span className="font-mono text-xs font-bold text-navy select-all">
                      {item.reference_code}
                    </span>
                  ),
                },
                {
                  key: 'category',
                  header: 'Category',
                  render: (item: FeedbackManageItem) => (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-bg border border-border text-navy-muted">
                      {item.category.replace('_', ' ')}
                    </span>
                  ),
                },
                {
                  key: 'subject',
                  header: 'Subject & Submitter',
                  render: (item: FeedbackManageItem) => (
                    <div className="max-w-md">
                      <div className="font-semibold text-navy text-xs truncate">
                        {item.subject}
                      </div>
                      <div className="text-[11px] text-navy-subtle truncate flex items-center gap-1.5 mt-0.5">
                        {item.submitting_user_name ? (
                          <span>
                            {item.submitting_user_name} ({item.submitting_user_role || 'User'})
                          </span>
                        ) : item.contact_name || item.contact_email ? (
                          <span>
                            Public: {item.contact_name || item.contact_email}
                          </span>
                        ) : (
                          <span className="italic">Anonymous Public Inquiry</span>
                        )}
                        {item.page_reference && (
                          <span className="text-teal font-mono text-[10px]">
                            &bull; {item.page_reference}
                          </span>
                        )}
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'status',
                  header: 'Status',
                  render: (item: FeedbackManageItem) => {
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
                  key: 'notes_count',
                  header: 'Notes',
                  render: (item: FeedbackManageItem) => (
                    <span className="text-xs text-navy-muted flex items-center gap-1">
                      <MessageSquare className="w-3 h-3 text-navy-subtle" />
                      <span>{item.notes_count}</span>
                    </span>
                  ),
                },
                {
                  key: 'created_at',
                  header: 'Date Logged',
                  render: (item: FeedbackManageItem) => (
                    <span className="text-[11px] text-navy-subtle">
                      {new Date(item.created_at).toLocaleDateString()}
                    </span>
                  ),
                },
                {
                  key: 'actions',
                  header: 'Action',
                  render: (item: FeedbackManageItem) => (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => fetchDetail(item.id)}
                      className="text-teal hover:bg-teal-light/50 flex items-center gap-1 text-xs"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Review</span>
                    </Button>
                  ),
                },
              ]}
              data={items}
              keyExtractor={(item) => item.id}
            />

            {items.length === 0 && !isLoading && (
              <div className="p-8 text-center text-xs text-navy-muted">
                No feedback inquiries match the selected criteria.
              </div>
            )}
          </Card>
        </div>
      )}
      {activeTab === 'submit' && (
        <Card className="max-w-2xl mx-auto bg-white shadow-sm p-6">
          <div className="mb-5 pb-4 border-b border-border">
            <h2 className="font-heading text-lg font-bold text-navy">
              Submit Staff / Faculty Feedback
            </h2>
            <p className="text-xs text-navy-muted mt-1">
              Your feedback is automatically linked to your authenticated session and institution.
            </p>
          </div>

          <div className="mb-5 p-3.5 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <strong className="block font-semibold text-amber-800">
                Notice: Feedback is NOT a Timetable Change Request
              </strong>
              <span>
                This channel is strictly for system defect reports, feature suggestions, or facility accessibility notices. To request a formal timetable modification, please contact your department scheduling coordinator directly.
              </span>
            </div>
          </div>

          {submitError && (
            <div className="mb-4 p-3 rounded-lg bg-coral-light/60 border border-coral/30 text-xs text-coral font-medium" role="alert">
              {submitError}
            </div>
          )}

          <form onSubmit={handleAuthenticatedSubmit} className="space-y-4">
            <FormField label="Feedback Category" htmlFor="auth-cat" required>
              <Select
                id="auth-cat"
                value={submitCategory}
                onChange={(e) => setSubmitCategory(e.target.value as AuthenticatedFeedbackCategory)}
                required
              >
                <option value="BUG_REPORT">Bug Report</option>
                <option value="SUGGESTION">Platform Suggestion</option>
                <option value="ACCESS_ISSUE">Room / Facility Accessibility Issue</option>
                <option value="SCHEDULING_ISSUE">Scheduling Conflict / Constraint Observation</option>
                <option value="OTHER">Other Feedback</option>
              </Select>
            </FormField>

            <FormField label="Optional Page or Resource Reference" htmlFor="auth-ref" helperText="e.g. Timetable Grid - Friday 14:00, Hall B-102, or Lab 301">
              <Input
                id="auth-ref"
                placeholder="e.g. Timetables -> Computer Lab 301"
                value={submitPageRef}
                onChange={(e) => setSubmitPageRef(e.target.value)}
                maxLength={255}
              />
            </FormField>

            <FormField
              label="Subject"
              htmlFor="auth-subj"
              required
              helperText={`${submitSubject.length}/200 characters`}
            >
              <Input
                id="auth-subj"
                placeholder="Concise summary of your observation or report"
                value={submitSubject}
                onChange={(e) => setSubmitSubject(e.target.value)}
                maxLength={200}
                required
              />
            </FormField>

            <FormField
              label="Detailed Message"
              htmlFor="auth-msg"
              required
              helperText={`${submitMessage.length}/5000 characters (min 10 characters)`}
            >
              <Textarea
                id="auth-msg"
                rows={5}
                placeholder="Describe the issue, facility access consideration, or suggestion in detail..."
                value={submitMessage}
                onChange={(e) => setSubmitMessage(e.target.value)}
                maxLength={5000}
                required
              />
            </FormField>

            <div className="p-3 rounded-lg bg-bg border border-border/70 text-[11px] text-navy-subtle flex items-start gap-2">
              <Lock className="w-3.5 h-3.5 text-navy-subtle shrink-0 mt-0.5" />
              <span>
                Passwords, tokens, and raw confidential student records are never automatically collected. Reviewers will address your feedback according to institutional support policies.
              </span>
            </div>

            <div className="pt-2 flex justify-end gap-3">
              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={isSubmittingFeedback}
                className="flex items-center gap-2"
              >
                <Send className="w-4 h-4" />
                <span>Submit Feedback</span>
              </Button>
            </div>
          </form>

          <Dialog
            isOpen={!!submitSuccess}
            onClose={() => setSubmitSuccess(null)}
            title="Feedback Submitted Successfully"
            footer={
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setSubmitSuccess(null);
                  setActiveTab('my-submissions');
                }}
              >
                View My Submissions
              </Button>
            }
          >
            <div className="space-y-4 text-xs">
              <div className="flex items-start gap-3 p-3.5 bg-teal-light/50 border border-teal/20 rounded-xl">
                <CheckCircle2 className="w-6 h-6 text-teal shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-teal-dark text-sm mb-1">
                    {submitSuccess?.message || 'Your feedback has been logged securely.'}
                  </p>
                  <p className="text-navy-muted leading-relaxed">
                    This inquiry has been persisted in the institutional database and assigned for coordinator triage.
                  </p>
                </div>
              </div>

              <div className="p-3.5 bg-surface border border-border rounded-xl space-y-1.5">
                <span className="text-[11px] uppercase tracking-wider text-navy-subtle font-semibold block">
                  Reference Tracking Code:
                </span>
                <div className="font-mono font-bold text-base text-navy tracking-wider select-all bg-white px-3 py-1.5 rounded border border-border/80 inline-block">
                  {submitSuccess?.referenceCode}
                </div>
              </div>
            </div>
          </Dialog>
        </Card>
      )}

      {activeTab === 'my-submissions' && (
        <Card className="bg-white overflow-hidden p-0">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <div>
              <h2 className="font-heading text-sm font-bold text-navy">
                My Submitted Inquiries
              </h2>
              <p className="text-xs text-navy-muted">
                Track status updates on your submitted suggestions and bug reports. Internal reviewer notes are strictly shielded.
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchMySubmissions}
              isLoading={isMySubmissionsLoading}
              className="flex items-center gap-1.5 text-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </Button>
          </div>

          <Table
            columns={[
              {
                key: 'reference_code',
                header: 'Reference Code',
                render: (sub: UserSubmittedFeedback) => (
                  <span className="font-mono text-xs font-bold text-navy select-all">
                    {sub.reference_code}
                  </span>
                ),
              },
              {
                key: 'category',
                header: 'Category',
                render: (sub: UserSubmittedFeedback) => (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-bg border border-border text-navy-muted">
                    {sub.category.replace('_', ' ')}
                  </span>
                ),
              },
              {
                key: 'subject',
                header: 'Subject & Description',
                render: (sub: UserSubmittedFeedback) => (
                  <div className="max-w-md">
                    <div className="font-semibold text-navy text-xs">{sub.subject}</div>
                    <div className="text-xs text-navy-muted line-clamp-2 mt-0.5">
                      {sub.message}
                    </div>
                    {sub.page_reference && (
                      <div className="text-[10px] text-teal font-mono mt-1">
                        Ref: {sub.page_reference}
                      </div>
                    )}
                  </div>
                ),
              },
              {
                key: 'status',
                header: 'Status',
                render: (sub: UserSubmittedFeedback) => {
                  const statusColors: Record<FeedbackStatus, 'ACTIVE' | 'WARNING' | 'ALERT' | 'INFO' | 'PENDING'> = {
                    new: 'ALERT',
                    reviewing: 'WARNING',
                    awaiting_information: 'INFO',
                    resolved: 'ACTIVE',
                    closed: 'PENDING',
                  };
                  return <StatusBadge status={statusColors[sub.status]} label={sub.status.toUpperCase()} size="sm" />;
                },
              },
              {
                key: 'created_at',
                header: 'Submitted',
                render: (sub: UserSubmittedFeedback) => (
                  <span className="text-[11px] text-navy-subtle">
                    {new Date(sub.created_at).toLocaleString()}
                  </span>
                ),
              },
            ]}
            data={mySubmissions}
            keyExtractor={(sub) => sub.id}
          />

          {mySubmissions.length === 0 && !isMySubmissionsLoading && (
            <div className="p-8 text-center text-xs text-navy-muted space-y-2">
              <p>You have not submitted any feedback yet.</p>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setActiveTab('submit')}
                className="mt-2"
              >
                Submit New Feedback
              </Button>
            </div>
          )}
        </Card>
      )}

      <Dialog
        isOpen={!!selectedId}
        onClose={() => {
          setSelectedId(null);
          setDetailItem(null);
        }}
        title={`Feedback Review: ${detailItem?.reference_code || ''}`}
        maxWidth="lg"
        footer={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setSelectedId(null);
              setDetailItem(null);
            }}
          >
            Close
          </Button>
        }
      >
        {isDetailLoading || !detailItem ? (
          <div className="p-8 text-center text-xs text-navy-muted">
            Loading submission details...
          </div>
        ) : (
          <div className="space-y-5 text-xs">
            <div className="p-4 bg-surface border border-border rounded-xl space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono font-bold text-sm text-navy">
                  {detailItem.reference_code}
                </span>
                <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-teal-light text-teal border border-teal/20">
                  {detailItem.category.replace('_', ' ')}
                </span>
              </div>

              <h3 className="font-bold text-navy text-sm">
                {detailItem.subject}
              </h3>

              <div className="text-[11px] text-navy-subtle flex flex-wrap gap-x-4 gap-y-1 pt-1 border-t border-border/60">
                <span>
                  <strong>Submitter:</strong>{' '}
                  {detailItem.submitting_user_name
                    ? `${detailItem.submitting_user_name} (${detailItem.submitting_user_role || 'User'})`
                    : detailItem.contact_name || detailItem.contact_email || 'Anonymous Public'}
                </span>
                {detailItem.contact_email && (
                  <span>
                    <strong>Email:</strong> {detailItem.contact_email}
                  </span>
                )}
                <span>
                  <strong>Logged:</strong> {new Date(detailItem.created_at).toLocaleString()}
                </span>
                {detailItem.page_reference && (
                  <span>
                    <strong>Page/Context:</strong> {detailItem.page_reference}
                  </span>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[11px] font-semibold text-navy uppercase tracking-wider">
                Submitted Message (Plaintext Rendered - Safe)
              </label>
              <div className="p-4 bg-bg border border-border rounded-xl text-navy whitespace-pre-wrap font-sans text-xs leading-relaxed max-h-60 overflow-y-auto">
                {detailItem.message}
              </div>
            </div>

            <div className="p-4 bg-white border border-border rounded-xl space-y-3">
              <h4 className="font-semibold text-navy text-xs">
                Triage & Workflow Status
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 items-end">
                <FormField label="Update Status" htmlFor="detail-status">
                  <Select
                    id="detail-status"
                    value={selectedNewStatus}
                    onChange={(e) => setSelectedNewStatus(e.target.value as FeedbackStatus)}
                    className="text-xs"
                  >
                    <option value="new">New</option>
                    <option value="reviewing">Reviewing</option>
                    <option value="awaiting_information">Awaiting Information</option>
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                  </Select>
                </FormField>

                <div className="flex justify-end">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleStatusUpdate}
                    isLoading={isUpdatingStatus}
                    className="w-full text-xs"
                  >
                    Save Status Change
                  </Button>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="block text-[11px] font-semibold text-navy uppercase tracking-wider">
                  Internal Reviewer Notes ({detailItem.internal_notes.length})
                </label>
                <span className="text-[10px] text-coral font-medium flex items-center gap-1">
                  <Lock className="w-3 h-3" />
                  Shielded from Submitter
                </span>
              </div>

              <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                {detailItem.internal_notes.map((note) => (
                  <div key={note.id} className="p-3 bg-bg border border-border rounded-lg text-xs space-y-1">
                    <div className="flex items-center justify-between text-[10px] text-navy-subtle">
                      <span className="font-semibold text-navy">{note.author_name}</span>
                      <span>{new Date(note.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-navy whitespace-pre-wrap">{note.note}</p>
                  </div>
                ))}

                {detailItem.internal_notes.length === 0 && (
                  <div className="p-3 text-center text-[11px] text-navy-subtle border border-dashed border-border rounded-lg">
                    No internal reviewer notes recorded yet.
                  </div>
                )}
              </div>

              <form onSubmit={handleAddNote} className="space-y-2 pt-2 border-t border-border">
                <FormField label="Add Internal Review Note" htmlFor="new-note-text">
                  <Textarea
                    id="new-note-text"
                    rows={2}
                    placeholder="Enter confidential notes, diagnosis, or triage plan..."
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    maxLength={2000}
                    className="text-xs"
                  />
                </FormField>
                <div className="flex justify-end">
                  <Button
                    type="submit"
                    variant="secondary"
                    size="sm"
                    disabled={!newNote.trim()}
                    isLoading={isAddingNote}
                    className="text-xs"
                  >
                    Add Note
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};
