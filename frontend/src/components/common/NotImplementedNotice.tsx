import React from 'react';
import { Hammer, Calendar, ShieldCheck } from 'lucide-react';
import { Card } from './Card';

export interface NotImplementedNoticeProps {
  moduleName: string;
  scheduledPhase: string;
  description: string;
  architectureDetails?: string[];
  className?: string;
}

export const NotImplementedNotice: React.FC<NotImplementedNoticeProps> = ({
  moduleName,
  scheduledPhase,
  description,
  architectureDetails,
  className = '',
}) => {
  return (
    <Card className={`border-border ${className}`}>
      <div className="flex flex-col sm:flex-row items-start gap-4 p-2">
        <div className="p-3 rounded-xl bg-ice-light border border-ice/30 text-navy shrink-0">
          <Hammer className="w-6 h-6 text-ice" aria-hidden="true" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2.5 mb-1.5">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-bg border border-border text-navy-muted">
              <Calendar className="w-3 h-3 text-navy-subtle" aria-hidden="true" />
              {scheduledPhase}
            </span>
            <span className="text-xs font-medium text-coral uppercase tracking-wider">
              Not implemented yet
            </span>
          </div>

          <h3 className="text-base sm:text-lg font-semibold text-navy font-heading mb-2">
            {moduleName}
          </h3>

          <p className="text-xs sm:text-sm text-navy-muted leading-relaxed mb-4">
            {description}
          </p>

          {architectureDetails && architectureDetails.length > 0 && (
            <div className="bg-bg/80 border border-border rounded-lg p-3.5 space-y-2 text-xs">
              <span className="font-semibold text-navy flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-teal" aria-hidden="true" />
                Planned Architectural Implementation:
              </span>
              <ul className="space-y-1.5 pl-4 list-disc text-navy-subtle">
                {architectureDetails.map((detail, idx) => (
                  <li key={idx} className="leading-normal">
                    {detail}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
