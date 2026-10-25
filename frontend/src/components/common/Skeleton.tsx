import React from 'react';

export interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'rect' | 'circle';
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'text',
  width,
  height,
}) => {
  const variantStyles = {
    text: 'h-4 rounded-md',
    rect: 'rounded-xl',
    circle: 'rounded-full',
  }[variant];

  const style: React.CSSProperties = {
    width: width || (variant === 'circle' ? height : undefined),
    height,
  };

  return (
    <div
      style={style}
      className={`animate-pulse bg-border-strong/40 ${variantStyles} ${className}`}
      aria-hidden="true"
    />
  );
};
