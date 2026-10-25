import React from 'react';
import { Dialog } from './Dialog';
import { Button } from './Button';
import { AlertTriangle, Info } from 'lucide-react';

export interface ConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
}

export const ConfirmationDialog: React.FC<ConfirmationDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isDestructive = false,
  isLoading = false,
}) => {
  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      maxWidth="sm"
      footer={
        <>
          <Button variant="secondary" size="sm" onClick={onClose} disabled={isLoading}>
            {cancelLabel}
          </Button>
          <Button
            variant={isDestructive ? 'danger' : 'primary'}
            size="sm"
            onClick={onConfirm}
            isLoading={isLoading}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="flex items-start gap-3.5 py-1">
        <div
          className={`p-2 rounded-lg shrink-0 ${
            isDestructive ? 'bg-coral-light text-coral' : 'bg-teal-light text-teal'
          }`}
          aria-hidden="true"
        >
          {isDestructive ? <AlertTriangle className="w-5 h-5" /> : <Info className="w-5 h-5" />}
        </div>
        <p className="text-sm text-navy-muted leading-relaxed">{message}</p>
      </div>
    </Dialog>
  );
};
