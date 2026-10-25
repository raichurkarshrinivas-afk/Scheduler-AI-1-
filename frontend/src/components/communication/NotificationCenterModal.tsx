import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bell,
  CheckCheck,
  Check,
  Clock,
  Moon,
  Calendar,
  AlertTriangle,
  Shield,
  Layers,
  RefreshCw,
  ExternalLink,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { Dialog } from '../common/Dialog';
import { Button } from '../common/Button';
import { StatusBadge } from '../common/StatusBadge';
import { api } from '../../services/api';
import {
  NotificationCategory,
  NotificationPreferences,
  CalendarStatus,
} from '../../types';

export interface NotificationCenterModalProps {
  isOpen: boolean;
  onClose: () => void;
  isSSEConnected: boolean;
  isSSEFallback: boolean;
}

export const NotificationCenterModal: React.FC<NotificationCenterModalProps> = ({
  isOpen,
  onClose,
  isSSEConnected,
  isSSEFallback,
}) => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'notifications' | 'preferences' | 'calendar'>('notifications');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [unreadOnly, setUnreadOnly] = useState<boolean>(false);

  // 1. Notifications Query
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
    enabled: isOpen && activeTab === 'notifications',
    staleTime: 10000,
  });

  // 2. Preferences Query
  const { data: preferences, refetch: refetchPrefs } = useQuery<NotificationPreferences>({
    queryKey: ['notification-preferences'],
    queryFn: () => api.communication.getPreferences(),
    enabled: isOpen && activeTab === 'preferences',
    staleTime: 30000,
  });

  // 3. Calendar Status Query
  const {
    data: calendarStatus,
    isLoading: isCalendarLoading,
    refetch: refetchCalendar,
  } = useQuery<CalendarStatus>({
    queryKey: ['calendar-status'],
    queryFn: () => api.communication.getCalendarStatus(),
    enabled: isOpen && activeTab === 'calendar',
    staleTime: 15000,
  });

  // Mark Read Mutation
  const markReadMutation = useMutation({
    mutationFn: (id: string) => api.communication.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-notifications-count'] });
    },
  });

  // Mark All Read Mutation
  const markAllReadMutation = useMutation({
    mutationFn: () => api.communication.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-notifications-count'] });
    },
  });

  // Update Preferences Mutation
  const updatePrefsMutation = useMutation({
    mutationFn: (updates: Partial<NotificationPreferences>) => api.communication.updatePreferences(updates),
    onSuccess: () => {
      refetchPrefs();
      queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
    },
  });

  // Calendar Sync Mutation
  const syncCalendarMutation = useMutation({
    mutationFn: () => api.communication.syncCalendar(),
    onSuccess: () => {
      refetchCalendar();
    },
  });

  // Disconnect Calendar Mutation
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
            <Shield className="w-2.5 h-2.5" />
            SECURITY {priority === 'URGENT' && '(URGENT)'}
          </span>
        );
      case 'ACADEMIC_CHANGE':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-light text-teal border border-teal/30">
            <Layers className="w-2.5 h-2.5" />
            ACADEMIC
          </span>
        );
      case 'OPERATIONAL_ALERT':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-light text-amber-800 border border-amber/30">
            <AlertTriangle className="w-2.5 h-2.5" />
            OPERATIONAL
          </span>
        );
      case 'SCHEDULED_REMINDER':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
            <Clock className="w-2.5 h-2.5" />
            REMINDER
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Communication & Notification Centre"
      description="Durable notifications, quiet hours preferences, live SSE stream, and calendar integration."
      maxWidth="lg"
      footer={
        <div className="flex items-center justify-between w-full">
          {/* Live Stream Status Indicator */}
          <div className="flex items-center gap-1.5 text-[11px] text-navy-muted">
            {isSSEConnected ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-teal" />
                <span className="font-medium text-teal">SSE Live Stream Active</span>
              </>
            ) : isSSEFallback ? (
              <>
                <WifiOff className="w-3.5 h-3.5 text-amber-600" />
                <span className="font-medium text-amber-600">Polling Fallback Mode</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-navy-subtle" />
                <span>Connecting Stream...</span>
              </>
            )}
          </div>
          <Button variant="primary" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Navigation Tabs */}
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setActiveTab('notifications')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === 'notifications'
                  ? 'bg-teal text-white shadow-subtle'
                  : 'text-navy-muted hover:text-navy hover:bg-bg'
              }`}
            >
              <Bell className="w-3.5 h-3.5" />
              <span>Notifications</span>
              {notifData?.unread_count ? (
                <span className="ml-1 px-1.5 py-0.2 rounded-full bg-coral text-white text-[10px] font-bold">
                  {notifData.unread_count}
                </span>
              ) : null}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('preferences')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === 'preferences'
                  ? 'bg-teal text-white shadow-subtle'
                  : 'text-navy-muted hover:text-navy hover:bg-bg'
              }`}
            >
              <Moon className="w-3.5 h-3.5" />
              <span>Quiet Hours & Rules</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('calendar')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === 'calendar'
                  ? 'bg-teal text-white shadow-subtle'
                  : 'text-navy-muted hover:text-navy hover:bg-bg'
              }`}
            >
              <Calendar className="w-3.5 h-3.5" />
              <span>Google Calendar</span>
            </button>
          </div>

          {activeTab === 'notifications' && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => markAllReadMutation.mutate()}
              isLoading={markAllReadMutation.isPending}
              disabled={!notifData?.unread_count}
              className="text-[11px] h-7 px-2"
            >
              <CheckCheck className="w-3 h-3 mr-1" />
              Mark All Read
            </Button>
          )}
        </div>

        {/* TAB 1: NOTIFICATIONS FEED */}
        {activeTab === 'notifications' && (
          <div className="space-y-3">
            {/* Filter Pills */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-1 overflow-x-auto py-1">
                {['ALL', 'ACADEMIC_CHANGE', 'OPERATIONAL_ALERT', 'SECURITY_EVENT', 'SCHEDULED_REMINDER'].map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setCategoryFilter(cat)}
                    className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                      categoryFilter === cat
                        ? 'bg-navy text-white'
                        : 'bg-bg text-navy-muted hover:text-navy hover:bg-surface border border-border'
                    }`}
                  >
                    {cat === 'ALL'
                      ? 'All'
                      : cat === 'ACADEMIC_CHANGE'
                      ? 'Academic'
                      : cat === 'OPERATIONAL_ALERT'
                      ? 'Operational'
                      : cat === 'SECURITY_EVENT'
                      ? 'Security'
                      : 'Reminders'}
                  </button>
                ))}
              </div>

              <label className="flex items-center gap-1.5 cursor-pointer text-[11px] text-navy-muted select-none">
                <input
                  type="checkbox"
                  checked={unreadOnly}
                  onChange={(e) => setUnreadOnly(e.target.checked)}
                  className="rounded border-border text-teal focus:ring-teal"
                />
                <span>Unread only</span>
              </label>
            </div>

            {/* List */}
            {isNotifLoading ? (
              <div className="py-12 text-center text-xs text-navy-muted">
                <div className="w-6 h-6 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                Loading notifications...
              </div>
            ) : !notifData?.items || notifData.items.length === 0 ? (
              <div className="p-8 text-center bg-bg rounded-xl border border-border text-xs text-navy-muted">
                <Bell className="w-6 h-6 text-navy-subtle mx-auto mb-1.5" />
                <p className="font-semibold text-navy">No notifications found</p>
                <p className="text-[11px]">You're all caught up with your schedule notices and operational alerts.</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
                {notifData.items.map((n) => (
                  <div
                    key={n.id}
                    className={`p-3 rounded-xl border transition-all ${
                      n.is_read
                        ? 'bg-surface/50 border-border/70 text-navy-muted'
                        : 'bg-white border-teal/30 shadow-subtle text-navy'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {getCategoryBadge(n.category, n.priority)}
                        {!n.is_read && (
                          <span className="w-1.5 h-1.5 rounded-full bg-coral animate-pulse" />
                        )}
                        {n.scheduled_for && !n.delivered_at && (
                          <span className="text-[10px] bg-amber-50 text-amber-700 px-1.5 py-0.2 rounded border border-amber-200">
                            Quiet Hours Held
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-navy-subtle">
                          {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        {!n.is_read && (
                          <button
                            type="button"
                            onClick={() => markReadMutation.mutate(n.id)}
                            className="p-1 rounded hover:bg-bg text-navy-subtle hover:text-teal transition-colors"
                            title="Mark as read"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="mt-1.5">
                      <h4 className="text-xs font-semibold leading-tight">{n.title}</h4>
                      <p className="text-[11px] text-navy-muted mt-0.5 leading-relaxed">{n.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: PREFERENCES & QUIET HOURS */}
        {activeTab === 'preferences' && (
          <div className="space-y-4 text-xs">
            {/* Quiet Hours Configuration */}
            <div className="p-4 rounded-xl bg-surface border border-border space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h4 className="font-heading font-bold text-navy text-sm flex items-center gap-1.5">
                    <Moon className="w-4 h-4 text-teal" />
                    Quiet Hours Delivery Protection
                  </h4>
                  <p className="text-[11px] text-navy-muted mt-0.5">
                    Non-urgent notifications and reminders are held during quiet hours and delivered once hours end.
                    Security events and urgent alerts bypass quiet hours immediately.
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
                  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-teal"></div>
                </label>
              </div>

              {preferences?.quiet_hours_enabled && (
                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border/80">
                  <div>
                    <label className="block text-[11px] font-semibold text-navy mb-1">
                      Start Time (Evening)
                    </label>
                    <input
                      type="time"
                      value={preferences.quiet_hours_start || '22:00'}
                      onChange={(e) =>
                        updatePrefsMutation.mutate({ quiet_hours_start: e.target.value })
                      }
                      className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-border bg-white"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-navy mb-1">
                      End Time (Morning)
                    </label>
                    <input
                      type="time"
                      value={preferences.quiet_hours_end || '07:00'}
                      onChange={(e) =>
                        updatePrefsMutation.mutate({ quiet_hours_end: e.target.value })
                      }
                      className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-border bg-white"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Category Preferences */}
            <div className="p-4 rounded-xl bg-surface border border-border space-y-3">
              <h4 className="font-heading font-bold text-navy text-sm">Category Delivery Toggles</h4>

              <div className="divide-y divide-border/60">
                <div className="py-2 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-navy block">Academic Changes</span>
                    <span className="text-[11px] text-navy-muted">Timetable releases, room shifts, exam seating</span>
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

                <div className="py-2 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-navy block">Operational Alerts</span>
                    <span className="text-[11px] text-navy-muted">System solver status, schedule generation notices</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={preferences?.notify_operational_alerts ?? true}
                    onChange={(e) =>
                      updatePrefsMutation.mutate({ notify_operational_alerts: e.target.checked })
                    }
                    className="rounded text-teal focus:ring-teal"
                  />
                </div>

                <div className="py-2 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-navy block">Security Events</span>
                    <span className="text-[11px] text-navy-muted">New device logins, session revocations (Always Urgent)</span>
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

                <div className="py-2 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-navy block">Scheduled Reminders</span>
                    <span className="text-[11px] text-navy-muted">Class reminders following the newest publication</span>
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
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: GOOGLE CALENDAR SYNC */}
        {activeTab === 'calendar' && (
          <div className="space-y-4 text-xs">
            {isCalendarLoading ? (
              <div className="py-12 text-center text-xs text-navy-muted">
                <div className="w-6 h-6 border-2 border-teal border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                Checking calendar integration status...
              </div>
            ) : !calendarStatus?.configured ? (
              /* Not Configured State */
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-950 space-y-3">
                <div className="flex items-start gap-2.5">
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-heading font-bold text-sm text-amber-900">
                      Google Calendar: Not configured
                    </h4>
                    <p className="text-xs text-amber-800 mt-0.5">
                      Google OAuth credentials are absent in the server environment. Google Calendar sync is optional.
                    </p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-white/80 border border-amber-200/80 font-mono text-[11px] whitespace-pre-wrap leading-relaxed text-navy">
                  {calendarStatus?.guidance ||
                    'Set GOOGLE_CALENDAR_ENABLED=True, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI in backend/.env to enable.'}
                </div>
              </div>
            ) : (
              /* Configured State */
              <div className="p-4 rounded-xl bg-surface border border-border space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-heading font-bold text-navy text-sm">
                        Secondary Academic Calendar Sync
                      </h4>
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
                    <p className="text-[11px] text-navy-muted mt-1 leading-relaxed">
                      Authoritative one-way sync into an isolated "Scheduler - Academic Calendar". Your primary calendar is never overwritten.
                    </p>
                  </div>
                </div>

                {calendarStatus.is_connected ? (
                  <div className="space-y-3 pt-2 border-t border-border">
                    <div className="grid grid-cols-2 gap-3 text-[11px]">
                      <div className="p-2.5 rounded-lg bg-white border border-border">
                        <span className="text-navy-subtle block">Synced Events Count</span>
                        <span className="font-heading font-bold text-base text-navy">
                          {calendarStatus.sync_event_count}
                        </span>
                      </div>
                      <div className="p-2.5 rounded-lg bg-white border border-border">
                        <span className="text-navy-subtle block">Last Synced</span>
                        <span className="font-heading font-bold text-xs text-navy">
                          {calendarStatus.last_synced_at
                            ? new Date(calendarStatus.last_synced_at).toLocaleString()
                            : 'Pending'}
                        </span>
                      </div>
                    </div>

                    {calendarStatus.last_error && (
                      <div className="p-2.5 rounded-lg bg-coral-light border border-coral/30 text-[11px] text-coral flex items-start gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
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
                  <div className="pt-2 border-t border-border flex items-center justify-between">
                    <span className="text-xs text-navy-muted">Ready to link your secondary Google Calendar.</span>
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
              </div>
            )}
          </div>
        )}
      </div>
    </Dialog>
  );
};
