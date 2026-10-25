import React from 'react';
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  XCircle,
  ShieldCheck,
  FileText,
  Radio,
} from 'lucide-react';

export type StatusVariant =
  | 'PUBLISHED'
  | 'DRAFT'
  | 'CHECKED'
  | 'ACTIVE'
  | 'ALERT'
  | 'CONFLICT'
  | 'PENDING'
  | 'OFFLINE';

export interface StatusBadgeProps {
  status: StatusVariant | string;
  label?: string;
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  size = 'md',
  className = '',
}) => {
  const normStatus = (status || '').toUpperCase() as StatusVariant;
  const displayLabel = label || normStatus;

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs gap-1' : 'px-2.5 py-1 text-xs gap-1.5 font-medium';

  const config: Record<
    StatusVariant,
    { bg: string; text: string; border: string; icon: React.ReactNode }
  > = {
    PUBLISHED: {
      bg: 'bg-teal-light',
      text: 'text-teal',
      border: 'border-teal/20',
      icon: <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />,
    },
    DRAFT: {
      bg: 'bg-bg',
      text: 'text-navy-muted',
      border: 'border-border-strong',
      icon: <FileText className="w-3.5 h-3.5" aria-hidden="true" />,
    },
    CHECKED: {
      bg: 'bg-ice-light',
      text: 'text-navy',
      border: 'border-ice/30',
      icon: <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />,
    },
    ACTIVE: {
      bg: 'bg-teal-light',
      text: 'text-teal',
      border: 'border-teal/20',
      icon: <Radio className="w-3.5 h-3.5" aria-hidden="true" />,
    },
    ALERT: {
      bg: 'bg-amber-light',
      text: 'text-amber-800',
      border: 'border-amber/30',
      icon: <AlertCircle className="w-3.5 h-3.5 text-amber-700" aria-hidden="true" />,
    },
    CONFLICT: {
      bg: 'bg-coral-light',
      text: 'text-coral',
      border: 'border-coral/20',
      icon: <XCircle className="w-3.5 h-3.5" aria-hidden="true" />,
    },
    PENDING: {
      bg: 'bg-lavender-light',
      text: 'text-navy',
      border: 'border-lavender/30',
      icon: <Clock className="w-3.5 h-3.5" aria-hidden="true" />,
    },
    OFFLINE: {
      bg: 'bg-bg',
      text: 'text-navy-subtle',
      border: 'border-border',
      icon: <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />,
    },
  };

  const current = config[normStatus] || {
    bg: 'bg-bg',
    text: 'text-navy',
    border: 'border-border',
    icon: <FileText className="w-3.5 h-3.5" aria-hidden="true" />,
  };

  return (
    <span
      className={`inline-flex items-center rounded-md border ${current.bg} ${current.text} ${current.border} ${sizeClasses} select-none ${className}`}
      role="status"
      aria-label={`Status: ${displayLabel}`}
    >
      <span className="shrink-0">{current.icon}</span>
      <span>{displayLabel}</span>
    </span>
  );
};
