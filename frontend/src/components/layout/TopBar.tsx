import React, { useState, useRef } from 'react';
import {
  Calendar,
  Bell,
  LogOut,
  Key,
  Monitor,
  ChevronDown,
  Building,
} from 'lucide-react';
import { UserProfile } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { useKeyboardTrap } from '../../hooks/useKeyboardTrap';

export interface TopBarProps {
  user: UserProfile;
  activeTerm: string;
  onTermChange?: (term: string) => void;
  onLogout: () => void;
  onChangePasswordClick: () => void;
  onManageSessionsClick: () => void;
  onNotificationsClick: () => void;
  unreadNotificationsCount?: number;
}

export const TopBar: React.FC<TopBarProps> = ({
  user,
  activeTerm,
  onTermChange,
  onLogout,
  onChangePasswordClick,
  onManageSessionsClick,
  onNotificationsClick,
  unreadNotificationsCount = 0,
}) => {
  const [profileOpen, setProfileOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  useKeyboardTrap(profileOpen, menuRef, () => setProfileOpen(false));

  const roleLabels: Record<string, string> = {
    INSTITUTION_ADMINISTRATOR: 'Administrator',
    TIMETABLE_COORDINATOR: 'Coordinator',
    EXAM_CONTROLLER: 'Exam Controller',
    TEACHER: 'Faculty',
    STUDENT: 'Student',
  };

  return (
    <header className="h-16 bg-surface border-b border-border px-4 sm:px-6 flex items-center justify-between z-30 sticky top-0 shadow-subtle">
      {/* Left: Institution Context & Active Term Selection */}
      <div className="flex items-center gap-3 sm:gap-4 min-w-0">
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-bg border border-border text-xs text-navy font-semibold shrink-0">
          <Building className="w-3.5 h-3.5 text-teal" aria-hidden="true" />
          <span>{user.institution_code || 'APEX'}</span>
        </div>

        {/* Academic Term Selector */}
        <div className="flex items-center gap-1.5 text-xs text-navy-muted">
          <Calendar className="w-3.5 h-3.5 text-navy-subtle shrink-0 hidden sm:inline" aria-hidden="true" />
          <span className="hidden md:inline text-navy-subtle">Term:</span>
          {onTermChange ? (
            <select
              value={activeTerm}
              onChange={(e) => onTermChange(e.target.value)}
              className="bg-transparent font-medium text-navy border-none focus-visible:outline-2 focus-visible:outline-teal rounded p-0.5 cursor-pointer text-xs"
              aria-label="Select active academic term"
            >
              <option value="Autumn 2026">Autumn 2026 (Active)</option>
              <option value="Spring 2026">Spring 2026 (Concluded)</option>
            </select>
          ) : (
            <span className="font-medium text-navy">{activeTerm}</span>
          )}
        </div>
      </div>

      {/* Right: Notifications & Profile Menu */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Notifications Entry Point */}
        <button
          type="button"
          onClick={onNotificationsClick}
          className="relative p-2 rounded-lg text-navy-muted hover:text-navy hover:bg-bg transition-colors focus-visible:outline-2 focus-visible:outline-teal"
          aria-label={`View notifications (${unreadNotificationsCount} unread)`}
        >
          <Bell className="w-4 h-4" aria-hidden="true" />
          {unreadNotificationsCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-coral animate-pulse" />
          )}
        </button>

        {/* Profile Menu Trigger */}
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setProfileOpen(!profileOpen)}
            className="flex items-center gap-2.5 p-1 sm:px-2.5 sm:py-1 rounded-lg border border-border hover:bg-bg transition-colors focus-visible:outline-2 focus-visible:outline-teal"
            aria-expanded={profileOpen}
            aria-haspopup="true"
            aria-label="User profile options"
          >
            <div className="w-7 h-7 rounded-full bg-teal text-white flex items-center justify-center font-bold text-xs select-none">
              {user.full_name?.charAt(0) || 'U'}
            </div>
            <div className="text-left hidden sm:block">
              <div className="text-xs font-semibold text-navy leading-tight truncate max-w-[120px]">
                {user.full_name}
              </div>
              <div className="text-[10px] text-navy-subtle leading-tight">
                {roleLabels[user.role] || user.role}
              </div>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-navy-subtle hidden sm:inline" aria-hidden="true" />
          </button>

          {/* Profile Dropdown */}
          {profileOpen && (
            <div
              className="absolute right-0 mt-2 w-64 bg-surface border border-border rounded-xl shadow-elevated p-2 space-y-1 animate-in fade-in zoom-in-95 duration-100 z-50 text-xs"
              role="menu"
            >
              <div className="px-3 py-2 border-b border-border/80">
                <div className="font-semibold text-navy truncate">{user.full_name}</div>
                <div className="text-navy-subtle truncate">{user.email}</div>
                <div className="mt-1.5 flex items-center gap-1.5">
                  <StatusBadge status="ACTIVE" label={roleLabels[user.role] || user.role} size="sm" />
                </div>
              </div>

              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setProfileOpen(false);
                  onManageSessionsClick();
                }}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-navy-muted hover:text-navy hover:bg-bg text-left transition-colors"
              >
                <Monitor className="w-3.5 h-3.5 text-navy-subtle" aria-hidden="true" />
                <span>Active Browser Sessions</span>
              </button>

              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setProfileOpen(false);
                  onChangePasswordClick();
                }}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-navy-muted hover:text-navy hover:bg-bg text-left transition-colors"
              >
                <Key className="w-3.5 h-3.5 text-navy-subtle" aria-hidden="true" />
                <span>Change Password</span>
              </button>

              <div className="pt-1 border-t border-border/80">
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setProfileOpen(false);
                    onLogout();
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-coral hover:bg-coral-light/50 text-left font-medium transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5 text-coral" aria-hidden="true" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
