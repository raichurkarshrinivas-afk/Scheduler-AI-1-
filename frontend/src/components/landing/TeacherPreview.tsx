import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import { Card } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';
import { Button } from '../common/Button';

export const TeacherPreview: React.FC = () => {
  return (
    <div className="space-y-4">
      {/* Synthetic Notice */}
      <div className="flex items-center justify-between text-xs text-navy-subtle bg-bg p-2.5 rounded-lg border border-border">
        <span className="font-semibold text-navy">Teacher Workspace Experience</span>
        <span className="italic">Illustrative synthetic preview &bull; No personal data</span>
      </div>

      <Card className="bg-white">
        {/* Header with Draft Status & Validation */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 mb-4 border-b border-border">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-heading font-semibold text-base text-navy">
                Dr. E. Smith (Computer Science)
              </span>
              <StatusBadge status="CHECKED" label="Checked Draft" size="sm" />
            </div>
            <p className="text-xs text-navy-muted">
              Term: Autumn 2026 &bull; 14 Contact Hours Allocated
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium bg-teal-light text-teal border border-teal/20">
              <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
              0 Clashes Detected
            </span>
          </div>
        </div>

        {/* Validation Summary Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          <div className="p-3 rounded-lg bg-bg border border-border">
            <span className="text-[11px] text-navy-subtle uppercase block">Max Hours</span>
            <span className="font-heading font-bold text-sm text-navy">16 hrs / wk</span>
          </div>
          <div className="p-3 rounded-lg bg-bg border border-border">
            <span className="text-[11px] text-navy-subtle uppercase block">Assigned</span>
            <span className="font-heading font-bold text-sm text-teal">14 hrs / wk</span>
          </div>
          <div className="p-3 rounded-lg bg-bg border border-border">
            <span className="text-[11px] text-navy-subtle uppercase block">Invigilation</span>
            <span className="font-heading font-bold text-sm text-navy">2 Sittings</span>
          </div>
          <div className="p-3 rounded-lg bg-bg border border-border">
            <span className="text-[11px] text-navy-subtle uppercase block">Unavailability</span>
            <span className="font-heading font-bold text-sm text-navy-muted">Fri 14:00+</span>
          </div>
        </div>

        {/* Sample Daily Teaching Schedule */}
        <div className="border border-border rounded-lg overflow-hidden text-xs">
          <div className="bg-bg/80 px-3 py-2 font-semibold text-navy-muted border-b border-border flex justify-between">
            <span>TODAY'S TEACHING ASSIGNMENTS (SAMPLE)</span>
            <span>WEDNESDAY</span>
          </div>
          <div className="divide-y divide-border">
            <div className="p-3 flex items-center justify-between hover:bg-bg/40">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded bg-teal-light text-teal font-semibold">09:00</div>
                <div>
                  <div className="font-semibold text-navy">CS-201: Data Structures & Algorithms</div>
                  <div className="text-navy-subtle text-[11px]">Lecture &bull; Room 204 &bull; Batch CS-A</div>
                </div>
              </div>
              <StatusBadge status="ACTIVE" label="Scheduled" size="sm" />
            </div>

            <div className="p-3 flex items-center justify-between hover:bg-bg/40">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded bg-ice-light text-navy font-semibold">13:30</div>
                <div>
                  <div className="font-semibold text-navy">CS-201L: Algorithms Laboratory (2 hrs)</div>
                  <div className="text-navy-subtle text-[11px]">Lab 3 &bull; Workstations 01-24 &bull; Batch CS-A1</div>
                </div>
              </div>
              <StatusBadge status="ACTIVE" label="Scheduled" size="sm" />
            </div>
          </div>
        </div>

        {/* Review Action Card */}
        <div className="mt-4 pt-3 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-navy-subtle">
          <span>Review feedback submission is audit-logged to institutional coordinator.</span>
          <Button variant="secondary" size="sm" disabled>
            Sign-off on Draft (Preview Only)
          </Button>
        </div>
      </Card>
    </div>
  );
};
