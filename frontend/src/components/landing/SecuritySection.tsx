import React from 'react';
import { ShieldCheck, Lock, Key, Database, RefreshCw, FileText } from 'lucide-react';
import { Card } from '../common/Card';

export const SecuritySection: React.FC = () => {
  const implementedFeatures = [
    {
      title: 'Multi-Tenant Data Isolation',
      desc: 'All institutional records are bound by composite foreign keys (institution_id) at the database engine level, preventing cross-tenant leakage.',
      icon: <Database className="w-5 h-5 text-teal" aria-hidden="true" />,
    },
    {
      title: 'Argon2id Password Hashing',
      desc: 'Standardized on RFC 9106 recommended interactive parameters (time_cost=3, memory_cost=65536, parallelism=4, hash_len=32).',
      icon: <Lock className="w-5 h-5 text-teal" aria-hidden="true" />,
    },
    {
      title: 'SHA-256 Digest-Only Session Storage',
      desc: 'Raw 256-bit session tokens are transported in HttpOnly browser cookies and never stored in plaintext in the database. Only SHA-256 digests are persisted.',
      icon: <Key className="w-5 h-5 text-teal" aria-hidden="true" />,
    },
    {
      title: 'Double-Submit CSRF Defense',
      desc: 'Mutating HTTP requests (POST, PUT, PATCH, DELETE) require a cryptographically random session-bound X-CSRF-Token header matching the CSRF cookie.',
      icon: <ShieldCheck className="w-5 h-5 text-teal" aria-hidden="true" />,
    },
    {
      title: 'Sliding-Window Rate Limiting',
      desc: 'Authentication and password reset endpoints are guarded by thread-safe sliding-window rate limiters mitigating credential stuffing attacks.',
      icon: <RefreshCw className="w-5 h-5 text-teal" aria-hidden="true" />,
    },
    {
      title: 'Audited Security Events without Secrets',
      desc: 'Logins, logouts, session revocations, and administrative password resets generate immutable audit records with passwords and tokens strictly excluded.',
      icon: <FileText className="w-5 h-5 text-teal" aria-hidden="true" />,
    },
  ];

  const plannedFeatures = [
    'Automated offline air-gapped verification tooling (Scheduled for Phase 6)',
    'Hardware security key / WebAuthn FIDO2 support (Planned roadmap)',
    'Distributed multi-node rate limiting via atomic Redis sliding windows (Documented in ADR 011)',
  ];

  return (
    <section id="security" className="py-16 sm:py-20 border-b border-border/70 bg-bg/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-xs font-semibold uppercase tracking-wider text-teal bg-teal-light px-3 py-1 rounded-full border border-teal/20">
            System Integrity
          </span>
          <h2 className="font-heading text-2xl sm:text-3xl font-bold text-navy tracking-tight mt-3 mb-3">
            Implemented Security Architecture
          </h2>
          <p className="text-sm sm:text-base text-navy-muted leading-relaxed">
            Engineered around strict tenant isolation, memory-hard cryptography, and zero storage of credentials in client localStorage.
          </p>
        </div>

        {/* Implemented Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
          {implementedFeatures.map((feat, idx) => (
            <Card key={idx} className="bg-white">
              <div className="p-2.5 rounded-xl bg-teal-light border border-teal/20 w-fit mb-3.5">
                {feat.icon}
              </div>
              <h3 className="font-heading text-base font-semibold text-navy mb-1.5">
                {feat.title}
              </h3>
              <p className="text-xs sm:text-sm text-navy-muted leading-relaxed">
                {feat.desc}
              </p>
            </Card>
          ))}
        </div>

        {/* Planned Roadmap Transparency Box */}
        <div className="bg-white border border-border rounded-xl p-5 shadow-subtle max-w-3xl mx-auto">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-navy-muted mb-2 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-ice" aria-hidden="true" />
            Roadmap Capabilities (Explicitly Planned for Future Releases)
          </h3>
          <ul className="text-xs text-navy-subtle space-y-1.5 pl-4 list-disc">
            {plannedFeatures.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
};
