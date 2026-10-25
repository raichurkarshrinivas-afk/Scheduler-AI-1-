import React from 'react';
import { Database, Sliders, PlayCircle, CheckSquare } from 'lucide-react';

export const WorkflowSection: React.FC = () => {
  const steps = [
    {
      number: '01',
      title: 'Import Institutional Data',
      desc: 'Load departments, academic terms, courses, teachers, enrolled cohorts, and physical room capacities.',
      icon: <Database className="w-5 h-5 text-teal" aria-hidden="true" />,
    },
    {
      number: '02',
      title: 'Configure Rules & Availability',
      desc: 'Set teacher availability preferences, lab workstation requirements, and room bench layout limits.',
      icon: <Sliders className="w-5 h-5 text-ice" aria-hidden="true" />,
    },
    {
      number: '03',
      title: 'Generate & Check Draft',
      desc: 'Run deterministic constraint solving to detect clashing rooms, teacher overlaps, or bench proximity conflicts.',
      icon: <PlayCircle className="w-5 h-5 text-amber-700" aria-hidden="true" />,
    },
    {
      number: '04',
      title: 'Review & Publish',
      desc: 'Conduct departmental stakeholder review, apply sign-offs, and publish locked schedules to students and faculty.',
      icon: <CheckSquare className="w-5 h-5 text-teal" aria-hidden="true" />,
    },
  ];

  return (
    <section id="workflow" className="py-16 sm:py-20 border-b border-border/70 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <span className="text-xs font-semibold uppercase tracking-wider text-teal bg-teal-light px-3 py-1 rounded-full border border-teal/20">
            Lifecycle Governance
          </span>
          <h2 className="font-heading text-2xl sm:text-3xl font-bold text-navy tracking-tight mt-3 mb-3">
            Draft &rarr; Check &rarr; Review &rarr; Publish
          </h2>
          <p className="text-sm sm:text-base text-navy-muted leading-relaxed">
            Every schedule advances through four audited stages, ensuring full institutional verification prior to candidate release.
          </p>
        </div>

        {/* 4-Step Process Grid */}
        <div className="relative">
          {/* Subtle horizontal connecting line on desktop */}
          <div
            className="hidden lg:block absolute top-7 left-12 right-12 h-0.5 bg-border -z-0"
            aria-hidden="true"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 relative z-10">
            {steps.map((step) => (
              <div key={step.number} className="flex flex-col items-start bg-surface p-5 rounded-xl border border-border shadow-subtle">
                <div className="flex items-center justify-between w-full mb-4">
                  <div className="w-12 h-12 rounded-xl bg-bg border border-border flex items-center justify-center shadow-subtle">
                    {step.icon}
                  </div>
                  <span className="font-heading font-bold text-xl text-navy-subtle/50">
                    {step.number}
                  </span>
                </div>

                <h3 className="font-heading text-base font-semibold text-navy mb-2">
                  {step.title}
                </h3>

                <p className="text-xs sm:text-sm text-navy-muted leading-relaxed">
                  {step.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
