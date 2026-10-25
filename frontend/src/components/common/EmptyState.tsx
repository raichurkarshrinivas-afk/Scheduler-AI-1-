import React from 'react';
import { Inbox } from 'lucide-react';
import { Button } from './Button';

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 sm:p-12 text-center bg-surface border border-border border-dashed rounded-xl ${className}`}
    >
      <div className="p-3.5 rounded-2xl bg-bg border border-border text-navy-muted mb-4 shadow-subtle">
        {icon || <Inbox className="w-8 h-8 text-navy-subtle" aria-hidden="true" />}
      </div>
      <h3 className="text-base font-semibold text-navy font-heading mb-1.5">{title}</h3>
      <p className="text-xs sm:text-sm text-navy-subtle max-w-sm mb-6 leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <Button variant="primary" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
