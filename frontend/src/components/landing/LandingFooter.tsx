import React from 'react';
import { ArrowUp, Shield } from 'lucide-react';

export interface LandingFooterProps {
  onPrivacyClick: () => void;
  onAccessibilityClick: () => void;
  onContactClick: () => void;
}

export const LandingFooter: React.FC<LandingFooterProps> = ({
  onPrivacyClick,
  onAccessibilityClick,
  onContactClick,
}) => {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <footer className="bg-white border-t border-border py-12 text-sm text-navy-muted">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-8 border-b border-border/70">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-teal flex items-center justify-center text-white font-bold text-lg font-heading shadow-subtle select-none">
              S
            </div>
            <div>
              <span className="font-heading font-bold text-base text-navy tracking-tight block">
                Scheduler
              </span>
              <span className="text-xs text-navy-subtle">
                Educational Timetable & Exam Seating Platform
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs sm:text-sm font-medium">
            <button
              onClick={onPrivacyClick}
              className="text-navy-muted hover:text-navy transition-colors focus-visible:outline-2 focus-visible:outline-teal rounded"
            >
              Privacy Policy
            </button>
            <button
              onClick={onAccessibilityClick}
              className="text-navy-muted hover:text-navy transition-colors focus-visible:outline-2 focus-visible:outline-teal rounded"
            >
              Accessibility Statement
            </button>
            <button
              onClick={onContactClick}
              className="text-navy-muted hover:text-navy transition-colors focus-visible:outline-2 focus-visible:outline-teal rounded"
            >
              Contact & Support
            </button>
            <button
              onClick={scrollToTop}
              className="inline-flex items-center gap-1.5 text-navy-muted hover:text-navy transition-colors focus-visible:outline-2 focus-visible:outline-teal rounded p-1"
              aria-label="Scroll back to top"
            >
              <ArrowUp className="w-4 h-4" aria-hidden="true" />
              <span>Back to Top</span>
            </button>
          </div>
        </div>

        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-navy-subtle">
          <div>
            &copy; {new Date().getFullYear()} Scheduler. Deterministic academic constraint resolution.
          </div>
          <div className="flex items-center gap-2">
            <Shield className="w-3.5 h-3.5 text-teal" aria-hidden="true" />
            <span>Strict Row-Level Institutional Isolation</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
