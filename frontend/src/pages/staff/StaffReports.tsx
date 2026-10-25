import React from 'react';
import { Printer } from 'lucide-react';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { NotImplementedNotice } from '../../components/common/NotImplementedNotice';

export const StaffReports: React.FC = () => {
  const reports = [
    {
      id: 'rep-01',
      title: 'Institutional Master Timetable (PDF)',
      desc: 'Complete tabular schedule breakdown across all academic cohorts and departments.',
      type: 'PDF Document',
    },
    {
      id: 'rep-02',
      title: 'Examination Seating Charts & Desk Slips (PDF)',
      desc: 'Printable door plans, desk tags, and alphabetical candidate registry by hall.',
      type: 'PDF Print Package',
    },
    {
      id: 'rep-03',
      title: 'Facility Utilization & Capacity Audit',
      desc: 'Metric breakdown of classroom occupancy rates, idle periods, and lab hours.',
      type: 'CSV / Data Export',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-xl sm:text-2xl font-bold text-navy">
          Institutional Reports & PDF Exports
        </h1>
        <p className="text-xs sm:text-sm text-navy-muted">
          Printable schedules, door charts, and capacity compliance documentation.
        </p>
      </div>

      <NotImplementedNotice
        moduleName="ReportLab PDF Generation & Export Engine"
        scheduledPhase="Scheduled for Phase 5"
        description="High-fidelity vector PDF generation for door seating charts, student hall tickets, and master matrices using Python ReportLab is scheduled for active generation in Phase 5. No mock downloads are presented."
        architectureDetails={[
          'Server-side vector PDF generation matching exact physical desk grid measurements',
          'Print-ready desk label slips with QR verification and candidate PRN barcodes',
        ]}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {reports.map((rep) => (
          <Card key={rep.id} title={rep.title}>
            <p className="text-xs text-navy-muted mb-4">{rep.desc}</p>
            <div className="pt-3 border-t border-border flex items-center justify-between">
              <span className="text-[11px] font-semibold text-navy-subtle bg-bg px-2 py-0.5 rounded">
                {rep.type}
              </span>
              <Button variant="secondary" size="sm" disabled leftIcon={<Printer className="w-3.5 h-3.5" />}>
                Export (Phase 5)
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
