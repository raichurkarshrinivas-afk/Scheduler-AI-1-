import React from 'react';
import { Calendar, MonitorCheck, LayoutGrid, ArrowRight } from 'lucide-react';
import { Card } from '../common/Card';

export interface ProductModulesProps {
  onModuleSelect: (moduleKey: 'timetables' | 'practicals' | 'seating') => void;
}

export const ProductModules: React.FC<ProductModulesProps> = ({ onModuleSelect }) => {
  const modules = [
    {
      key: 'timetables' as const,
      title: 'Class & Practical Timetables',
      description:
        'Generate conflict-free weekly schedules balancing room capacities, teacher availabilities, and cohort curricula.',
      icon: <Calendar className="w-6 h-6 text-teal" aria-hidden="true" />,
      tag: 'Academic Timetabling',
      tagColor: 'bg-teal-light text-teal border-teal/20',
      actionLabel: 'Explore Timetable Matrix',
      visual: (
        <div className="bg-bg/80 border border-border rounded-lg p-3 space-y-2 select-none" aria-hidden="true">
          <div className="flex gap-2 text-[11px] font-semibold text-navy-muted">
            <span className="w-16">MON</span>
            <span className="w-16">TUE</span>
            <span className="w-16">WED</span>
          </div>
          <div className="flex gap-2">
            <div className="w-16 h-7 rounded bg-teal/20 border border-teal/30 flex items-center justify-center text-[10px] font-bold text-teal">CS-201</div>
            <div className="w-16 h-7 rounded bg-ice/20 border border-ice/30 flex items-center justify-center text-[10px] font-bold text-navy">MAT-101</div>
            <div className="w-16 h-7 rounded bg-lavender/20 border border-lavender/30 flex items-center justify-center text-[10px] font-bold text-navy">PHY-102</div>
          </div>
          <div className="flex gap-2">
            <div className="w-16 h-10 rounded bg-navy text-white flex flex-col items-center justify-center text-[9px] font-bold">
              <span>LAB CS</span>
              <span className="text-[8px] text-teal-light">2 hrs</span>
            </div>
            <div className="w-16 h-10 rounded bg-amber/20 border border-amber/30 flex items-center justify-center text-[10px] font-bold text-amber-800">TUT-1</div>
            <div className="w-16 h-10 rounded bg-bg border border-border border-dashed flex items-center justify-center text-[9px] text-navy-subtle">Free</div>
          </div>
        </div>
      ),
    },
    {
      key: 'practicals' as const,
      title: 'Practical Examination Sittings',
      description:
        'Coordinate laboratory rotations, workstation hardware features, operating systems, and invigilation batches.',
      icon: <MonitorCheck className="w-6 h-6 text-ice" aria-hidden="true" />,
      tag: 'Laboratory Operations',
      tagColor: 'bg-ice-light text-navy border-ice/30',
      actionLabel: 'Explore Lab Workstations',
      visual: (
        <div className="bg-bg/80 border border-border rounded-lg p-3 space-y-2 select-none" aria-hidden="true">
          <div className="flex items-center justify-between text-[11px] text-navy-muted">
            <span className="font-semibold">Lab 3 (30 Terminals)</span>
            <span className="text-teal font-medium">GPU Ready</span>
          </div>
          <div className="grid grid-cols-4 gap-1.5">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
              <div
                key={n}
                className={`h-7 rounded border flex items-center justify-center text-[10px] font-medium ${
                  n === 3
                    ? 'bg-amber-light border-amber text-amber-900 font-bold'
                    : 'bg-white border-border text-navy-muted'
                }`}
              >
                WS-{n < 10 ? `0${n}` : n}
              </div>
            ))}
          </div>
          <div className="text-[10px] text-navy-subtle text-center">Batch A: 14 Candidates Allocated</div>
        </div>
      ),
    },
    {
      key: 'seating' as const,
      title: 'Theory Examination Seating',
      description:
        'Enforce anti-cheating orthogonal spacing and candidate distribution with strictly one candidate per usable bench.',
      icon: <LayoutGrid className="w-6 h-6 text-amber-700" aria-hidden="true" />,
      tag: 'Anti-Cheating Seating',
      tagColor: 'bg-amber-light text-amber-900 border-amber/30',
      actionLabel: 'Explore Seating Layouts',
      visual: (
        <div className="bg-bg/80 border border-border rounded-lg p-3 space-y-2 select-none" aria-hidden="true">
          <div className="flex items-center justify-between text-[11px] text-navy-muted">
            <span className="font-semibold">Hall B (Alternating)</span>
            <span className="text-coral font-medium text-[10px]">Buffer Desks</span>
          </div>
          <div className="grid grid-cols-4 gap-1.5">
            {[
              { label: 'CS', ok: true },
              { label: 'Empty', ok: false },
              { label: 'EE', ok: true },
              { label: 'Empty', ok: false },
              { label: 'Empty', ok: false },
              { label: 'ME', ok: true },
              { label: 'Empty', ok: false },
              { label: 'CS', ok: true },
            ].map((d, i) => (
              <div
                key={i}
                className={`h-7 rounded border flex items-center justify-center text-[10px] font-semibold ${
                  d.ok
                    ? 'bg-teal-light border-teal/40 text-teal'
                    : 'bg-bg border-border text-navy-subtle/50 border-dashed'
                }`}
              >
                {d.label}
              </div>
            ))}
          </div>
          <div className="text-[10px] text-navy-subtle text-center">0 Cohort Adjacencies Detected</div>
        </div>
      ),
    },
  ];

  return (
    <section id="product-modules" className="py-16 sm:py-20 border-b border-border/70 bg-bg/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="font-heading text-2xl sm:text-3xl font-bold text-navy tracking-tight mb-3">
            Three Integrated Scheduling Modules
          </h2>
          <p className="text-sm sm:text-base text-navy-muted leading-relaxed">
            Every module operates within unified institutional constraints, sharing rooms, faculty availabilities, and academic term definitions.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
          {modules.map((mod) => (
            <Card
              key={mod.key}
              hoverable
              onClick={() => onModuleSelect(mod.key)}
              className="flex flex-col justify-between h-full bg-white transition-all hover:-translate-y-0.5"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="p-2.5 rounded-xl bg-bg border border-border shadow-subtle">
                    {mod.icon}
                  </div>
                  <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${mod.tagColor}`}>
                    {mod.tag}
                  </span>
                </div>

                <div>
                  <h3 className="font-heading text-lg font-semibold text-navy mb-1.5">{mod.title}</h3>
                  <p className="text-xs sm:text-sm text-navy-muted leading-relaxed">
                    {mod.description}
                  </p>
                </div>

                <div className="pt-2">{mod.visual}</div>
              </div>

              <div className="pt-5 mt-4 border-t border-border flex items-center justify-between text-xs font-semibold text-teal hover:text-teal-hover transition-colors">
                <span>{mod.actionLabel}</span>
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};
