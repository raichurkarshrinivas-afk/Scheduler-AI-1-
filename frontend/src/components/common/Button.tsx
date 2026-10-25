import React, { ButtonHTMLAttributes, forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium transition-colors rounded-lg focus-visible:outline-2 focus-visible:outline-teal focus-visible:outline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed select-none';

    const sizeStyles = {
      sm: 'px-3 py-1.5 text-xs gap-1.5',
      md: 'px-4 py-2 text-sm gap-2',
      lg: 'px-5 py-2.5 text-base gap-2.5',
    }[size];

    const variantStyles = {
      primary: 'bg-teal text-white hover:bg-teal-hover shadow-subtle active:scale-[0.99]',
      secondary: 'bg-white text-navy border border-border hover:bg-bg hover:border-border-strong shadow-subtle',
      danger: 'bg-coral text-white hover:bg-red-700 shadow-subtle active:scale-[0.99]',
      ghost: 'bg-transparent text-navy hover:bg-navy/5 active:bg-navy/10',
      outline: 'bg-transparent border border-teal text-teal hover:bg-teal-light',
    }[variant];

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${baseStyles} ${sizeStyles} ${variantStyles} ${className}`}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin shrink-0" aria-hidden="true" />
        ) : (
          leftIcon && <span className="shrink-0" aria-hidden="true">{leftIcon}</span>
        )}
        <span>{children}</span>
        {!isLoading && rightIcon && (
          <span className="shrink-0" aria-hidden="true">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
