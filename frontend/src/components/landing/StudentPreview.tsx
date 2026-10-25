import React from 'react';
import { Bell, MapPin, Ticket } from 'lucide-react';
import { Card } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';

export const StudentPreview: React.FC = () => {
  return (
    <div className="space-y-4">
      {/* Synthetic Notice */}
      <div className="flex items-center justify-between text-xs text-navy-subtle bg-bg p-2.5 rounded-lg border border-border">
        <span className="font-semibold text-navy">Student Mobile / Web Experience</span>
        <span className="italic">Illustrative synthetic preview &bull; No personal data</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Next Class Card */}
        <Card className="bg-white border-l-4 border-l-teal">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-teal uppercase tracking-wider">
              Next Academic Session
            </span>
            <span className="text-xs text-navy-subtle">Starts in 45m</span>
          </div>

          <h4 className="font-heading font-semibold text-base text-navy mb-1">
            Data Structures & Algorithms
          </h4>

          <div className="flex items-center gap-2 text-xs text-navy-muted mb-3">
            <span>Lecture CS-201</span>
            <span>&bull;</span>
            <span className="flex items-center gap-1 font-medium text-navy">
              <MapPin className="w-3.5 h-3.5 text-teal" aria-hidden="true" />
              Room 204
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-bg text-xs flex justify-between items-center text-navy-subtle">
            <span>09:00 - 10:30</span>
            <span className="font-medium text-navy">Dr. E. Smith</span>
          </div>
        </Card>

        {/* Practical Exam Workstation */}
        <Card className="bg-white border-l-4 border-l-ice">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-ice uppercase tracking-wider">
              Assigned Lab Terminal
            </span>
            <StatusBadge status="ACTIVE" label="Verified" size="sm" />
          </div>

          <h4 className="font-heading font-semibold text-base text-navy mb-1">
            Computing Systems Lab Exam
          </h4>

          <div className="flex items-center gap-2 text-xs text-navy-muted mb-3">
            <span>Batch CS-A1</span>
            <span>&bull;</span>
            <span className="font-bold text-navy">Workstation #07</span>
          </div>

          <div className="p-2.5 rounded-lg bg-bg text-xs flex justify-between items-center text-navy-subtle">
            <span>Lab 3 &bull; Linux Ubuntu 24.04</span>
            <span className="font-medium text-teal">GPU Allocated</span>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Theory Exam Desk Assignment */}
        <Card className="bg-white border-l-4 border-l-amber">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-amber-800 uppercase tracking-wider">
              Theory Exam Hall Ticket
            </span>
            <Ticket className="w-4 h-4 text-amber-700" aria-hidden="true" />
          </div>

          <div className="flex items-baseline justify-between mb-2">
            <div>
              <div className="text-xs text-navy-subtle">Assigned Examination Desk</div>
              <div className="font-heading font-bold text-xl text-navy">Bench D-14</div>
            </div>
            <span className="text-xs bg-amber-light text-amber-900 border border-amber/30 px-2 py-0.5 rounded font-medium">
              Single-Candidate Desk
            </span>
          </div>

          <div className="text-xs text-navy-muted bg-bg p-2 rounded border border-border/80 space-y-1">
            <div className="flex justify-between">
              <span>Exam Hall:</span>
              <strong className="text-navy">Auditorium Main Floor</strong>
            </div>
            <div className="flex justify-between">
              <span>Anti-Cheating Spacing:</span>
              <span className="text-teal font-medium">Orthogonal Separation Verified</span>
            </div>
          </div>
        </Card>

        {/* Change Notification Banner */}
        <Card className="bg-white border-l-4 border-l-lavender">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-navy uppercase tracking-wider flex items-center gap-1.5">
              <Bell className="w-3.5 h-3.5 text-lavender" aria-hidden="true" />
              Schedule Notification
            </span>
            <span className="text-[11px] text-navy-subtle">Today, 08:15</span>
          </div>

          <h5 className="font-heading font-semibold text-sm text-navy mb-1">
            Timetable Revision Published
          </h5>

          <p className="text-xs text-navy-muted leading-relaxed mb-3">
            Room change for Friday tutorial: relocated from Room 102 to Lecture Theatre 1 to accommodate audio-visual requirements.
          </p>

          <div className="text-[11px] text-teal font-semibold">
            &check; Automatically updated in your personal weekly matrix
          </div>
        </Card>
      </div>
    </div>
  );
};
