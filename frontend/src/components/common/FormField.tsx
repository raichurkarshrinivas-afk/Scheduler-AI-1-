import React, { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes, forwardRef } from 'react';

export interface FormFieldProps {
  label: string;
  htmlFor: string;
  error?: string;
  helperText?: string;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
}

export const FormField: React.FC<FormFieldProps> = ({
  label,
  htmlFor,
  error,
  helperText,
  required,
  children,
  className = '',
}) => {
  return (
    <div className={`space-y-1.5 ${className}`}>
      <div className="flex justify-between items-center">
        <label htmlFor={htmlFor} className="block text-xs font-semibold text-navy uppercase tracking-wider">
          {label}
          {required && <span className="text-coral ml-1" aria-hidden="true">*</span>}
        </label>
      </div>

      {children}

      {error ? (
        <p id={`${htmlFor}-error`} className="text-xs text-coral font-medium flex items-center gap-1" role="alert">
          <span aria-hidden="true">&bull;</span>
          {error}
        </p>
      ) : helperText ? (
        <p id={`${htmlFor}-helper`} className="text-xs text-navy-subtle">
          {helperText}
        </p>
      ) : null}
    </div>
  );
};

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', error, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={`w-full px-3.5 py-2 text-sm bg-white border rounded-lg transition-colors text-navy placeholder:text-navy-subtle/60 focus-visible:outline-2 focus-visible:outline-teal focus-visible:outline-offset-1 disabled:bg-bg disabled:text-navy-subtle disabled:cursor-not-allowed ${
          error ? 'border-coral ring-1 ring-coral/20' : 'border-border hover:border-border-strong'
        } ${className}`}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className = '', error, children, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={`w-full px-3.5 py-2 text-sm bg-white border rounded-lg transition-colors text-navy focus-visible:outline-2 focus-visible:outline-teal focus-visible:outline-offset-1 disabled:bg-bg disabled:cursor-not-allowed ${
          error ? 'border-coral ring-1 ring-coral/20' : 'border-border hover:border-border-strong'
        } ${className}`}
        {...props}
      >
        {children}
      </select>
    );
  }
);
Select.displayName = 'Select';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className = '', error, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={`w-full px-3.5 py-2 text-sm bg-white border rounded-lg transition-colors text-navy placeholder:text-navy-subtle/60 focus-visible:outline-2 focus-visible:outline-teal focus-visible:outline-offset-1 disabled:bg-bg disabled:cursor-not-allowed ${
          error ? 'border-coral ring-1 ring-coral/20' : 'border-border hover:border-border-strong'
        } ${className}`}
        {...props}
      />
    );
  }
);
Textarea.displayName = 'Textarea';
