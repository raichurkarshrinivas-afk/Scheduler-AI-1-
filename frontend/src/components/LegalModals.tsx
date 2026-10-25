import React from 'react';
import { Dialog } from './common/Dialog';
import { Button } from './common/Button';
import { ShieldCheck, Eye } from 'lucide-react';

export const PrivacyModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({
  isOpen,
  onClose,
}) => {
  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Privacy Policy & Tenant Data Isolation"
      maxWidth="lg"
      footer={<Button variant="primary" size="sm" onClick={onClose}>Close</Button>}
    >
      <div className="space-y-4 text-xs sm:text-sm text-navy-muted leading-relaxed">
        <div className="p-3 rounded-lg bg-teal-light text-teal border border-teal/20 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span className="font-semibold text-navy">Zero-Third-Party Tracking Policy</span>
        </div>
        <p>
          Scheduler is strictly designed for educational institutions. We do not sell, license, or transmit candidate or institutional records to third parties.
        </p>
        <h4 className="font-semibold text-navy text-sm font-heading">Row-Level Tenant Boundaries</h4>
        <p>
          Every student, instructor, and schedule entity is bound to its home institution through mandatory foreign keys (<code className="bg-bg px-1 py-0.5 rounded border border-border">institution_id</code>). All API queries strictly enforce institutional tenancy. Cross-institution access attempts are denied immediately.
        </p>
        <h4 className="font-semibold text-navy text-sm font-heading">Session Tokens & Cookies</h4>
        <p>
          Authentication uses server-side browser sessions stored in <code className="bg-bg px-1 py-0.5 rounded border border-border">HttpOnly</code>, <code className="bg-bg px-1 py-0.5 rounded border border-border">SameSite=Lax</code> cookies. Raw tokens are never stored in localStorage, and only SHA-256 token digests are persisted in the database.
        </p>
      </div>
    </Dialog>
  );
};

export const AccessibilityModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({
  isOpen,
  onClose,
}) => {
  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Accessibility Statement (WCAG 2.1 AA)"
      maxWidth="lg"
      footer={<Button variant="primary" size="sm" onClick={onClose}>Close</Button>}
    >
      <div className="space-y-4 text-xs sm:text-sm text-navy-muted leading-relaxed">
        <div className="p-3 rounded-lg bg-ice-light text-navy border border-ice/30 flex items-center gap-2">
          <Eye className="w-4 h-4 text-ice shrink-0" aria-hidden="true" />
          <span className="font-semibold text-navy">Built for Full Keyboard and Assistive Technology Access</span>
        </div>
        <p>
          Scheduler is committed to ensuring digital accessibility for students, teachers, and administrative staff with disabilities:
        </p>
        <ul className="list-disc pl-5 space-y-1.5 text-navy-subtle">
          <li><strong>No Color-Only State:</strong> All schedule conflict alerts, publication states, and validation tags pair color with distinct text labels and SVG icons.</li>
          <li><strong>Visible Focus Indicators:</strong> Interactive controls feature high-contrast 2px teal focus rings on keyboard navigation.</li>
          <li><strong>Non-Drag Alternatives:</strong> Where spatial timetables or seating grids support direct interaction, equivalent keyboard modals and manual coordinates are provided.</li>
          <li><strong>Reduced Motion Support:</strong> Respects <code className="bg-bg px-1 py-0.5 rounded border border-border">prefers-reduced-motion: reduce</code> media queries, pausing spatial animations and disabling parallax.</li>
          <li><strong>Semantic HTML & Landmarks:</strong> Proper ARIA roles, table headers, and modal focus traps.</li>
        </ul>
      </div>
    </Dialog>
  );
};
