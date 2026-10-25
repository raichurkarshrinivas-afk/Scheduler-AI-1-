import React, { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { UserRole } from '../../types';

export interface MobileNavigationProps {
  role: UserRole;
  activePath: string;
  onNavigate: (path: string) => void;
}

export const MobileNavigation: React.FC<MobileNavigationProps> = ({
  role,
  activePath,
  onNavigate,
}) => {
  const [open, setOpen] = useState(false);
  const isStudent = role === 'STUDENT';

  const staffNavItems = [
    { id: 'overview', label: 'Overview' },
    { id: 'timetables', label: 'Timetables' },
    { id: 'examinations', label: 'Examinations' },
    { id: 'resources', label: 'Resources' },
    { id: 'publish-history', label: 'Publish & history' },
    { id: 'reports', label: 'Reports' },
    { id: 'feedback', label: 'Feedback' },
    { id: 'settings', label: 'Settings' },
  ];

  const studentNavItems = [
    { id: 'home', label: 'Home' },
    { id: 'timetable', label: 'Timetable' },
    { id: 'practicals', label: 'Practicals' },
    { id: 'exams-seats', label: 'Exams/seats' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'feedback', label: 'Feedback' },
    { id: 'profile', label: 'Profile' },
  ];

  const navItems = isStudent ? studentNavItems : staffNavItems;

  return (
    <div className="lg:hidden bg-surface border-b border-border px-4 py-2.5 flex items-center justify-between sticky top-16 z-20 shadow-subtle">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-navy uppercase tracking-wider">
          {navItems.find((n) => n.id === activePath)?.label || 'Workspace'}
        </span>
      </div>

      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="p-1.5 rounded-lg border border-border text-navy-muted hover:text-navy hover:bg-bg flex items-center gap-1.5 text-xs font-medium focus-visible:outline-2 focus-visible:outline-teal"
        aria-expanded={open}
        aria-label="Toggle mobile workspace navigation"
      >
        {open ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
        <span>Menu</span>
      </button>

      {open && (
        <div className="absolute top-full left-0 right-0 bg-surface border-b border-border p-4 shadow-elevated grid grid-cols-2 gap-2 animate-in slide-in-from-top-2 duration-150">
          {navItems.map((item) => {
            const isActive = activePath === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  onNavigate(item.id);
                  setOpen(false);
                }}
                className={`p-2.5 rounded-lg text-xs font-medium text-left transition-colors ${
                  isActive
                    ? 'bg-teal-light text-teal font-semibold border border-teal/20'
                    : 'bg-bg text-navy hover:bg-border/50 border border-border/60'
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
