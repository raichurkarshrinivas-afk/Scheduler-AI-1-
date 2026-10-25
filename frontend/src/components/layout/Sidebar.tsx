import React from 'react';
import {
  LayoutDashboard,
  Calendar,
  Layers,
  Building2,
  FileCheck2,
  FileSpreadsheet,
  MessageSquare,
  Settings,
  Home,
  Clock,
  Monitor,
  Ticket,
  Bell,
  User,
} from 'lucide-react';
import { UserRole } from '../../types';

export interface SidebarProps {
  role: UserRole;
  activePath: string;
  onNavigate: (path: string) => void;
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  role,
  activePath,
  onNavigate,
  className = '',
}) => {
  const isStudent = role === 'STUDENT';

  const staffNavItems = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'timetables', label: 'Timetables', icon: <Calendar className="w-4 h-4" /> },
    { id: 'examinations', label: 'Examinations', icon: <Layers className="w-4 h-4" /> },
    { id: 'resources', label: 'Resources', icon: <Building2 className="w-4 h-4" /> },
    { id: 'publish-history', label: 'Publish & history', icon: <FileCheck2 className="w-4 h-4" /> },
    { id: 'reports', label: 'Reports', icon: <FileSpreadsheet className="w-4 h-4" /> },
    { id: 'feedback', label: 'Feedback', icon: <MessageSquare className="w-4 h-4" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
  ];

  const studentNavItems = [
    { id: 'home', label: 'Home', icon: <Home className="w-4 h-4" /> },
    { id: 'timetable', label: 'Timetable', icon: <Clock className="w-4 h-4" /> },
    { id: 'practicals', label: 'Practicals', icon: <Monitor className="w-4 h-4" /> },
    { id: 'exams-seats', label: 'Exams/seats', icon: <Ticket className="w-4 h-4" /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell className="w-4 h-4" /> },
    { id: 'feedback', label: 'Feedback', icon: <MessageSquare className="w-4 h-4" /> },
    { id: 'profile', label: 'Profile', icon: <User className="w-4 h-4" /> },
  ];

  const navItems = isStudent ? studentNavItems : staffNavItems;

  return (
    <aside
      className={`w-60 bg-surface border-r border-border flex flex-col justify-between shrink-0 select-none ${className}`}
      aria-label="Application Sidebar Navigation"
    >
      <div className="p-4">
        {/* Brand Header */}
        <div className="flex items-center gap-2.5 px-3 py-2 mb-6">
          <div className="w-7 h-7 rounded-lg bg-teal flex items-center justify-center text-white font-bold text-base font-heading shadow-subtle">
            S
          </div>
          <div>
            <span className="font-heading font-bold text-base text-navy tracking-tight block">
              Scheduler
            </span>
            <span className="text-[10px] text-navy-subtle uppercase tracking-wider block font-semibold">
              {isStudent ? 'Student Workspace' : 'Staff Workspace'}
            </span>
          </div>
        </div>

        {/* Navigation Item List */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = activePath === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-colors text-left focus-visible:outline-2 focus-visible:outline-teal ${
                  isActive
                    ? 'bg-teal-light text-teal font-semibold shadow-subtle'
                    : 'text-navy-muted hover:text-navy hover:bg-bg'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <span className={`shrink-0 ${isActive ? 'text-teal' : 'text-navy-subtle'}`}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* System Tenancy Badge at bottom */}
      <div className="p-4 border-t border-border/80">
        <div className="p-2.5 rounded-lg bg-bg border border-border text-[11px] text-navy-subtle space-y-0.5">
          <div className="font-semibold text-navy">Scheduler Engine</div>
          <div>Deterministic &bull; Air-Gap Capable</div>
        </div>
      </div>
    </aside>
  );
};
