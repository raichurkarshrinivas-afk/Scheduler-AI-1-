import React from 'react';
import { AlertCircle, RefreshCw, ShieldAlert } from 'lucide-react';
import { Button } from './Button';

export interface ErrorPanelProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  isPermissionDenied?: boolean;
  className?: string;
}

export const ErrorPanel: React.FC<ErrorPanelProps> = ({
  title,
  message,
  onRetry,
  isPermissionDenied = false,
  className = '',
}) => {
  const defaultTitle = isPermissionDenied ? 'Access Denied' : 'Unable to complete request';

  return (
    <div
      role="alert"
      className={`p-5 rounded-xl border ${
        isPermissionDenied
          ? 'bg-amber-light border-amber/30 text-amber-950'
          : 'bg-coral-light border-coral/30 text-coral'
      } ${className}`}
    >
      <div className="flex items-start gap-3.5">
        <div className="shrink-0 p-1 rounded-lg" aria-hidden="true">
          {isPermissionDenied ? (
            <ShieldAlert className="w-5 h-5 text-amber-700" />
          ) : (
            <AlertCircle className="w-5 h-5 text-coral" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold font-heading mb-1">{title || defaultTitle}</h4>
          <p className="text-xs text-navy-muted leading-relaxed mb-3">{message}</p>
          {onRetry && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onRetry}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Try Again
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
