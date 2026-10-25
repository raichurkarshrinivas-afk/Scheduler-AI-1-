import React, { useRef } from 'react';
import { X } from 'lucide-react';
import { useKeyboardTrap } from '../../hooks/useKeyboardTrap';

export interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl';
}

export const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  maxWidth = 'md',
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);
  useKeyboardTrap(isOpen, dialogRef, onClose);

  if (!isOpen) return null;

  const maxWidthClass = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  }[maxWidth];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy/40 backdrop-blur-[2px] transition-opacity"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      aria-describedby={description ? 'dialog-description' : undefined}
    >
      <div
        ref={dialogRef}
        className={`w-full ${maxWidthClass} bg-surface border border-border rounded-xl shadow-elevated overflow-hidden animate-in fade-in zoom-in-95 duration-150`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-bg/50">
          <div>
            <h2 id="dialog-title" className="text-base font-semibold text-navy font-heading">
              {title}
            </h2>
            {description && (
              <p id="dialog-description" className="text-xs text-navy-subtle mt-0.5">
                {description}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-navy-subtle hover:text-navy hover:bg-bg transition-colors focus-visible:outline-2 focus-visible:outline-teal"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="p-6 max-h-[75vh] overflow-y-auto">{children}</div>

        {footer && (
          <div className="flex items-center justify-end gap-3 px-6 py-3.5 border-t border-border bg-bg/50">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
