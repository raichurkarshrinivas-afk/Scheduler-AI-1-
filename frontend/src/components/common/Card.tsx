import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  action,
  className = '',
  onClick,
  hoverable = false,
}) => {
  return (
    <div
      onClick={onClick}
      className={`bg-surface border border-border rounded-xl shadow-subtle p-5 transition-all ${
        hoverable ? 'hover:shadow-card hover:border-border-strong cursor-pointer' : ''
      } ${className}`}
    >
      {(title || action) && (
        <div className="flex items-start justify-between gap-4 mb-4 pb-3 border-b border-border/70">
          <div>
            {title && (
              <h3 className="text-base font-semibold text-navy font-heading">{title}</h3>
            )}
            {subtitle && (
              <p className="text-xs text-navy-subtle mt-0.5">{subtitle}</p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
};

export interface MetricCardProps {
  label: string;
  value: string | number;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  change,
  trend = 'neutral',
  icon,
  className = '',
}) => {
  const trendClasses = {
    up: 'text-teal bg-teal-light',
    down: 'text-coral bg-coral-light',
    neutral: 'text-navy-subtle bg-bg',
  }[trend];

  return (
    <div className={`bg-surface border border-border rounded-xl shadow-subtle p-4 ${className}`}>
      <div className="flex items-center justify-between text-navy-subtle mb-2">
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
        {icon && <span className="p-1.5 rounded-lg bg-bg text-navy-muted">{icon}</span>}
      </div>
      <div className="flex items-baseline justify-between mt-1">
        <span className="text-2xl font-bold text-navy font-heading">{value}</span>
        {change && (
          <span className={`text-xs px-2 py-0.5 rounded-md font-medium ${trendClasses}`}>
            {change}
          </span>
        )}
      </div>
    </div>
  );
};
