import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

export const FAQSection: React.FC = () => {
  const [openIdx, setOpenIdx] = useState<number | null>(0);

  const faqs = [
    {
      q: 'Does Scheduler use external AI models or third-party LLM APIs?',
      a: 'No. Core scheduling, conflict detection, and exam seating are solved deterministically using combinatorial constraint programming (Google OR-Tools CP-SAT) and heuristic algorithms. This guarantees 100% reproducible, auditable outputs with zero recurring cloud API costs, no hallucinated constraints, and complete offline capability.',
    },
    {
      q: 'How does multi-tenancy prevent cross-institution data leaks?',
      a: 'Every institutional record in the database is tagged with an institution_id foreign key, and composite foreign key constraints are enforced at the PostgreSQL engine level. Furthermore, backend FastAPI dependency injection strictly validates tenant ownership before fulfilling any query.',
    },
    {
      q: 'What is the theory examination seating rule?',
      a: 'Scheduler enforces a strict policy of one candidate per usable bench. In addition, orthogonal spacing constraints ensure that candidates taking the same subject or enrolled in the same cohort are never seated adjacent to each other (left, right, directly in front, or directly behind).',
    },
    {
      q: 'How are user accounts created and recovered?',
      a: 'Public self-registration is disabled to protect academic boundaries. All accounts are created by institutional administrators. If a user forgets credentials, they follow a verified institutional administrative reset workflow where an administrator generates a secure temporary password with mandatory change upon first login.',
    },
    {
      q: 'Can students access draft or unpublished timetables?',
      a: 'No. Students have strictly read-only access restricted to published timetables and their own individual exam hall tickets and desk allocations. Internal draft matrices, unverified changes, and other students’ personal seat assignments are completely inaccessible.',
    },
  ];

  return (
    <section id="faq" className="py-16 sm:py-20 border-b border-border/70 bg-white">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-xl mx-auto mb-12">
          <span className="text-xs font-semibold uppercase tracking-wider text-teal bg-teal-light px-3 py-1 rounded-full border border-teal/20">
            Frequently Answered Questions
          </span>
          <h2 className="font-heading text-2xl sm:text-3xl font-bold text-navy tracking-tight mt-3 mb-2">
            Clear Answers on Architecture & Operations
          </h2>
          <p className="text-sm text-navy-muted">
            Engineered for deterministic institutional certainty.
          </p>
        </div>

        <div className="space-y-3">
          {faqs.map((item, idx) => {
            const isOpen = openIdx === idx;
            return (
              <div
                key={idx}
                className="border border-border rounded-xl bg-surface overflow-hidden shadow-subtle transition-colors"
              >
                <button
                  type="button"
                  onClick={() => setOpenIdx(isOpen ? null : idx)}
                  className="w-full text-left px-5 py-4 flex items-center justify-between gap-4 font-heading font-semibold text-sm sm:text-base text-navy hover:text-teal transition-colors focus-visible:outline-2 focus-visible:outline-teal"
                  aria-expanded={isOpen}
                >
                  <span>{item.q}</span>
                  <ChevronDown
                    className={`w-4 h-4 text-navy-subtle shrink-0 transition-transform duration-200 ${
                      isOpen ? 'rotate-180 text-teal' : ''
                    }`}
                    aria-hidden="true"
                  />
                </button>

                {isOpen && (
                  <div className="px-5 pb-5 pt-1 text-xs sm:text-sm text-navy-muted leading-relaxed border-t border-border/60 animate-in fade-in duration-150">
                    {item.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
