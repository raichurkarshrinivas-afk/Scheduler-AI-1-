import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bell,
  ShieldCheck,
  CheckCircle2,
  Clock,
  AlertCircle,
  Check,
  CheckCheck,
  Moon,
  Calendar,
  Layers,
  AlertTriangle,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { StatusBadge } from '../../components/common/StatusBadge';
import { api } from '../../services/api';
import {
  StudentChangeNotice,
  NotificationCategory,
  NotificationPreferences,
  CalendarStatus,
} from '../../types';

export const StudentNotifications: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'notifications' | 'releases' | 'preferences' | 'calendar'>('notifications');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [unreadOnly, setUnreadOnly] = useState<boolean>(false);

  // 1. In-App Notifications Query
  const {
    data: notifData,
    isLoading: isNotifLoading,
  } = useQuery({
    queryKey: ['notifications', categoryFilter, unreadOnly],
    queryFn: () =>
      api.communication.getNotifications({
        category: categoryFilter === 'ALL' ? undefined : categoryFilter,
        unread_only: unreadOnly,
        limit: 50,
      }),
    staleTime: 10000,
  });

  // 2. Immutable Audit Feed Query
  const {
    data: notices,
    isLoading: isNoticesLoading,
    error: noticesError,
    refetch: refetchNotices,
  } = useQuery<StudentChangeNotice[]>({
    queryKey: ['student-recent-changes'],
    queryFn: () => api.student.getRecentChanges(),
    staleTime: 30000,
  });

  // 3. Preferences Query
  const { data: preferences, refetch: refetchPrefs } = useQuery<NotificationPreferences>({
    queryKey: ['notification-preferences'],
    queryFn: () => api.communication.getPreferences(),
    enabled: activeTab === 'preferences',
    staleTime: 30000,
  });

  // 4. Calendar Status Query
  const {
    data: calendarStatus,
    isLoading: isCalendarLoading,
    refetch: refetchCalendar,
  } = useQuery<CalendarStatus>({
    queryKey: ['calendar-status'],
    queryFn: () => api.communication.getCalendarStatus(),
    enabled: activeTab === 'calendar',
    staleTime: 15000,
  });

  // Mutations
  const markReadMutation = useMutation({
    mutationFn: (id: string) => api.communication.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-notifications-count'] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => api.communication.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-notifications-count'] });
    },
  });

  const updatePrefsMutation = useMutation({
    mutationFn: (updates: Partial<NotificationPreferences>) => api.communication.updatePreferences(updates),
    onSuccess: () => {
      refetchPrefs();
      queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
    },
  });

  const syncCalendarMutation = useMutation({
    mutationFn: () => api.communication.syncCalendar(),
    onSuccess: () => {
      refetchCalendar();
    },
  });

  const disconnectCalendarMutation = useMutation({
    mutationFn: () => api.communication.disconnectCalendar(),
    onSuccess: () => {
      refetchCalendar();
    },
  });

  const getCategoryBadge = (cat: NotificationCategory, priority: string) => {
    switch (cat) {
      case 'SECURITY_EVENT':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-coral-light text-coral border border-coral/30">
            SECURITY {priority === 'URGENT' && '(URGENT)'}
          </span>
        );
      case 'ACADEMIC_CHANGE':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-light text-teal border border-teal/30">
            ACADEMIC
          </span>
        );
      case 'OPERATIONAL_ALERT':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-light text-amber-800 border border-amber/30">
            OPERATIONAL
          </span>
        );
      case 'SCHEDULED_REMINDER':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
            REMINDER
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
              Notification Centre & Change Notices
            </h1>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-teal-light text-teal font-semibold border border-teal/20">
              Live Feed
            </span>
          </div>
          <p className="text-xs sm:text-sm text-navy-muted mt-0.5">
            Durable in-app notifications, quiet hours delivery preferences, and published schedule releases.
          </p>
        </div>

        {activeTab === 'notifications' && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => markAllReadMutation.mutate()}
            isLoading={markAllReadMutation.isPending}
            disabled={!notifData?.unread_count}
          >
            <CheckCheck className="w-3.5 h-3.5 mr-1.5" />
            Mark All Read
          </Button>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1.5 border-b border-border pb-2 overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveTab('notifications')}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'notifications'
              ? 'bg-teal text-white shadow-subtle'
              : 'text-navy-muted hover:text-navy hover:bg-surface'
          }`}
        >
          <Bell className="w-3.5 h-3.5" />
          <span>My Notifications</span>
          {notifData?.unread_count ? (
            <span className="ml-1 px-1.5 py-0.2 rounded-full bg-coral text-white text-[10px] font-bold">
              {notifData.unread_count}
            </span>
          ) : null}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('releases')}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'releases'
              ? 'bg-teal text-white shadow-subtle'
              : 'text-navy-muted hover:text-navy hover:bg-surface'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Immutable Audit Releases</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('preferences')}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'preferences'
              ? 'bg-teal text-white shadow-subtle'
              : 'text-navy-muted hover:text-navy hover:bg-surface'
          }`}
        >
          <Moon className="w-3.5 h-3.5" />
          <span>Quiet Hours</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('calendar')}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            activeTab === 'calendar'
              ? 'bg-teal text-white shadow-subtle'
              : 'text-navy-muted hover:text-navy hover:bg-surface'
          }`}
        >
          <Calendar className="w-3.5 h-3.5" />
          <span>Google Calendar</span>
        </button>
      </div>

      {/* TAB 1: IN-APP NOTIFICATIONS */}
      {activeTab === 'notifications' && (
        <div className="space-y-4">
          {/* Category Filters */}
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-1 overflow-x-auto py-1">
              {['ALL', 'ACADEMIC_CHANGE', 'OPERATIONAL_ALERT', 'SECURITY_EVENT', 'SCHEDULED_REMINDER'].map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setCategoryFilter(cat)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                    categoryFilter === cat
                      ? 'bg-navy text-white shadow-subtle'
                      : 'bg-white text-navy-muted hover:text-navy hover:bg-surface border border-border'
                  }`}
                >
                  {cat === 'ALL'
                    ? 'All'
                    : cat === 'ACADEMIC_CHANGE'
                    ? 'Academic Changes'
                    : cat === 'OPERATIONAL_ALERT'
                    ? 'Operational'
                    : cat === 'SECURITY_EVENT'
                    ? 'Security'
                    : 'Reminders'}
                </button>
              ))}
            </div>

            <label className="flex items-center gap-1.5 cursor-pointer text-xs text-navy-muted select-none">
              <input
                type="checkbox"
                checked={unreadOnly}
                onChange={(e) => setUnreadOnly(e.target.checked)}
                className="rounded border-border text-teal focus:ring-teal"
              />
              <span>Unread only</span>
            </label>
          </div>

          {/* Feed Content */}
          {isNotifLoading ? (
            <div className="py-20 text-center space-y-3">
              <div className="w-8 h-8 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-navy-muted">Loading notifications...</p>
            </div>
          ) : !notifData?.items || notifData.items.length === 0 ? (
            <Card className="text-center py-12 space-y-2 bg-white">
              <CheckCircle2 className="w-8 h-8 text-teal mx-auto" />
              <h3 className="font-heading font-bold text-navy text-base">You're All Caught Up</h3>
              <p className="text-xs text-navy-muted max-w-sm mx-auto">
                No active notifications found for your account under the selected filter.
              </p>
            </Card>
          ) : (
            <div className="space-y-3">
              {notifData.items.map((n) => (
                <Card
                  key={n.id}
                  className={`transition-all ${
                    n.is_read
                      ? 'bg-surface/50 border-border/80'
                      : 'bg-white border-teal/40 shadow-subtle'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-2">
                    <div className="flex items-start gap-2.5">
                      <Bell
                        className={`w-4 h-4 shrink-0 mt-0.5 ${
                          n.is_read ? 'text-navy-subtle' : 'text-teal'
                        }`}
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-heading font-semibold text-sm text-navy">{n.title}</h3>
                          {getCategoryBadge(n.category, n.priority)}
                          {!n.is_read && (
                            <span className="w-2 h-2 rounded-full bg-coral animate-pulse" />
                          )}
                          {n.scheduled_for && !n.delivered_at && (
                            <span className="text-[10px] bg-amber-50 text-amber-800 px-2 py-0.5 rounded border border-amber-200">
                              Quiet Hours Protection
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-[11px] text-navy-subtle">
                        {new Date(n.created_at).toLocaleString()}
                      </span>
                      {!n.is_read && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-xs text-teal hover:bg-teal-light"
                          onClick={() => markReadMutation.mutate(n.id)}
                        >
                          <Check className="w-3.5 h-3.5 mr-1" />
                          Mark Read
                        </Button>
                      )}
                    </div>
                  </div>

                  <div className="pl-6 text-xs text-navy-muted leading-relaxed">
                    {n.message}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: IMMUTABLE RELEASES */}
      {activeTab === 'releases' && (
        <div className="space-y-3">
          {isNoticesLoading ? (
            <div className="py-20 text-center space-y-3">
              <div className="w-8 h-8 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-navy-muted">Loading audit release feed...</p>
            </div>
          ) : noticesError ? (
            <div className="p-6 rounded-xl bg-surface border border-border text-center space-y-2">
              <AlertCircle className="w-8 h-8 text-coral mx-auto" />
              <h3 className="font-heading font-bold text-navy text-sm">Failed to Load Notices</h3>
              <p className="text-xs text-navy-muted">{(noticesError as any)?.message || 'An error occurred.'}</p>
              <Button variant="secondary" size="sm" onClick={() => refetchNotices()}>
                Retry
              </Button>
            </div>
          ) : !notices || notices.length === 0 ? (
            <Card className="text-center py-12 space-y-2 bg-white">
              <CheckCircle2 className="w-8 h-8 text-teal mx-auto" />
              <h3 className="font-heading font-bold text-navy text-base">All Schedules Up to Date</h3>
              <p className="text-xs text-navy-muted max-w-sm mx-auto">
                No schedule modifications or publication notices have been issued yet for your enrolled units.
              </p>
            </Card>
          ) : (
            notices.map((n) => (
              <Card key={n.id} className="bg-white">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-2">
                  <div className="flex items-start gap-2.5">
                    <Bell className="w-4 h-4 text-teal shrink-0 mt-0.5" aria-hidden="true" />
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-heading font-semibold text-sm text-navy">{n.event_type}</h3>
                        <span className="text-[10px] font-bold bg-teal text-white px-2 py-0.5 rounded-full font-mono">
                          v{n.version_number}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="text-left sm:text-right text-[11px] text-navy-subtle shrink-0">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-teal" />
                      {new Date(n.published_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="pl-6 space-y-2 text-xs">
                  <p className="text-navy-muted leading-relaxed">
                    {n.note || 'Official academic release published. Schedules and reservations committed transactionally.'}
                  </p>

                  <div className="flex items-center gap-3 pt-2 border-t border-border text-[11px] text-navy-subtle">
                    <span className="flex items-center gap-1 text-teal font-medium">
                      <ShieldCheck className="w-3.5 h-3.5" /> Immutable Audit Release
                    </span>
                    <span>&bull;</span>
                    <span className="font-mono text-[10px]">Release ID: {n.id}</span>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* TAB 3: QUIET HOURS & PREFERENCES */}
      {activeTab === 'preferences' && (
        <div className="space-y-4 max-w-2xl">
          <Card className="p-5 bg-white space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-heading font-bold text-navy text-base flex items-center gap-2">
                  <Moon className="w-4 h-4 text-teal" />
                  Quiet Hours Non-Urgent Delivery Protection
                </h3>
                <p className="text-xs text-navy-muted mt-1 leading-relaxed">
                  During quiet hours, routine timetable reminders and non-urgent notices are held in your outbox queue and delivered after quiet hours end.
                  Urgent security events always bypass quiet hours immediately.
                </p>
              </div>

              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={preferences?.quiet_hours_enabled || false}
                  onChange={(e) =>
                    updatePrefsMutation.mutate({ quiet_hours_enabled: e.target.checked })
                  }
                  className="sr-only peer"
                />
                <div className="w-10 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-teal"></div>
              </label>
            </div>

            {preferences?.quiet_hours_enabled && (
              <div className="grid grid-cols-2 gap-4 pt-3 border-t border-border">
                <div>
                  <label className="block text-xs font-semibold text-navy mb-1">
                    Quiet Hours Start Time
                  </label>
                  <input
                    type="time"
                    value={preferences.quiet_hours_start || '22:00'}
                    onChange={(e) =>
                      updatePrefsMutation.mutate({ quiet_hours_start: e.target.value })
                    }
                    className="w-full text-xs px-3 py-2 rounded-lg border border-border bg-surface text-navy"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-navy mb-1">
                    Quiet Hours End Time
                  </label>
                  <input
                    type="time"
                    value={preferences.quiet_hours_end || '07:00'}
                    onChange={(e) =>
                      updatePrefsMutation.mutate({ quiet_hours_end: e.target.value })
                    }
                    className="w-full text-xs px-3 py-2 rounded-lg border border-border bg-surface text-navy"
                  />
                </div>
              </div>
            )}
          </Card>

          <Card className="p-5 bg-white space-y-3">
            <h3 className="font-heading font-bold text-navy text-sm">Notification Channels & Delivery Types</h3>
            <div className="divide-y divide-border/60 text-xs">
              <div className="py-2.5 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-navy block">Academic Changes</span>
                  <span className="text-navy-muted text-[11px]">Published timetable sessions, classroom changes, seating</span>
                </div>
                <input
                  type="checkbox"
                  checked={preferences?.notify_academic_changes ?? true}
                  onChange={(e) =>
                    updatePrefsMutation.mutate({ notify_academic_changes: e.target.checked })
                  }
                  className="rounded text-teal focus:ring-teal"
                />
              </div>

              <div className="py-2.5 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-navy block">Scheduled Reminders</span>
                  <span className="text-navy-muted text-[11px]">Upcoming lecture and examination sitting reminders</span>
                </div>
                <input
                  type="checkbox"
                  checked={preferences?.notify_scheduled_reminders ?? true}
                  onChange={(e) =>
                    updatePrefsMutation.mutate({ notify_scheduled_reminders: e.target.checked })
                  }
                  className="rounded text-teal focus:ring-teal"
                />
              </div>

              <div className="py-2.5 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-navy block">Security Alerts</span>
                  <span className="text-navy-muted text-[11px]">Password updates and new active browser sessions</span>
                </div>
                <input
                  type="checkbox"
                  checked={preferences?.notify_security_events ?? true}
                  onChange={(e) =>
                    updatePrefsMutation.mutate({ notify_security_events: e.target.checked })
                  }
                  className="rounded text-teal focus:ring-teal"
                />
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 4: GOOGLE CALENDAR */}
      {activeTab === 'calendar' && (
        <div className="max-w-2xl space-y-4">
          {isCalendarLoading ? (
            <div className="py-16 text-center text-xs text-navy-muted">
              <div className="w-8 h-8 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              Checking calendar integration status...
            </div>
          ) : !calendarStatus?.configured ? (
            <Card className="p-5 bg-amber-50 border-amber-200 text-amber-950 space-y-3">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-heading font-bold text-sm text-amber-900">
                    Google Calendar: Not configured
                  </h3>
                  <p className="text-xs text-amber-800 mt-0.5">
                    Google Calendar synchronization is an optional service requiring authorized credentials from the institution administrator.
                  </p>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-white/80 border border-amber-200/80 font-mono text-xs whitespace-pre-wrap leading-relaxed text-navy">
                {calendarStatus?.guidance ||
                  'Google OAuth credentials are not configured on this server.'}
              </div>
            </Card>
          ) : (
            <Card className="p-5 bg-white space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-heading font-bold text-navy text-base">
                      Secondary Academic Calendar Sync
                    </h3>
                    <StatusBadge
                      status={
                        calendarStatus.status === 'CONNECTED'
                          ? 'ACTIVE'
                          : calendarStatus.status === 'REVOKED'
                          ? 'FAILED'
                          : 'DRAFT'
                      }
                      label={calendarStatus.status}
                      size="sm"
                    />
                  </div>
                  <p className="text-xs text-navy-muted mt-1 leading-relaxed">
                    Authoritative one-way sync. Timetable sessions and exam seatings are synced to "Scheduler - Academic Calendar" in your Google account.
                  </p>
                </div>
              </div>

              {calendarStatus.is_connected ? (
                <div className="space-y-3 pt-3 border-t border-border">
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-lg bg-surface border border-border">
                      <span className="text-navy-subtle block">Synced Events Count</span>
                      <span className="font-heading font-bold text-xl text-navy mt-1 block">
                        {calendarStatus.sync_event_count}
                      </span>
                    </div>
                    <div className="p-3 rounded-lg bg-surface border border-border">
                      <span className="text-navy-subtle block">Last Sync Time</span>
                      <span className="font-heading font-bold text-xs text-navy mt-2 block">
                        {calendarStatus.last_synced_at
                          ? new Date(calendarStatus.last_synced_at).toLocaleString()
                          : 'Never'}
                      </span>
                    </div>
                  </div>

                  {calendarStatus.last_error && (
                    <div className="p-3 rounded-lg bg-coral-light border border-coral/30 text-xs text-coral flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{calendarStatus.last_error}</span>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => syncCalendarMutation.mutate()}
                      isLoading={syncCalendarMutation.isPending}
                    >
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                      Sync Now
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-coral hover:bg-coral-light/50"
                      onClick={() => disconnectCalendarMutation.mutate()}
                      isLoading={disconnectCalendarMutation.isPending}
                    >
                      Disconnect Calendar
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="pt-3 border-t border-border flex items-center justify-between">
                  <span className="text-xs text-navy-muted">Ready to connect your Google account.</span>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={async () => {
                      const res = await api.communication.getCalendarAuthUrl();
                      if (res?.auth_url) {
                        window.location.href = res.auth_url;
                      }
                    }}
                  >
                    <ExternalLink className="w-3.5 h-3.5 mr-1.5" />
                    Connect Google Calendar
                  </Button>
                </div>
              )}
            </Card>
          )}
        </div>
      )}
    </div>
  );
};
