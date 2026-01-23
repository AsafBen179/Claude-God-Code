/**
 * Button Component
 *
 * Professional, accessible button with multiple variants and sizes.
 * Follows WCAG 2.1 AA accessibility guidelines.
 */

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '../../lib/utils';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'accent' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: cn(
    'bg-primary text-primary-foreground',
    'hover:bg-primary/90',
    'active:bg-primary/80 active:scale-[0.98]',
    'shadow-sm hover:shadow-md hover:shadow-primary/20'
  ),
  secondary: cn(
    'bg-muted text-foreground',
    'border border-border',
    'hover:bg-muted/80 hover:border-border/80',
    'active:bg-muted/60 active:scale-[0.98]'
  ),
  ghost: cn(
    'bg-transparent text-muted-foreground',
    'hover:bg-muted hover:text-foreground',
    'active:bg-muted/80'
  ),
  accent: cn(
    'bg-accent text-accent-foreground',
    'hover:bg-accent/90',
    'active:bg-accent/80 active:scale-[0.98]',
    'shadow-sm hover:shadow-md hover:shadow-accent/20'
  ),
  danger: cn(
    'bg-danger text-danger-foreground',
    'hover:bg-danger/90',
    'active:bg-danger/80 active:scale-[0.98]'
  ),
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-base gap-2.5',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          // Base styles
          'inline-flex items-center justify-center',
          'font-medium rounded-lg',
          'transition-all duration-200 ease-out',
          'select-none',
          // Focus styles (accessibility)
          'focus-visible:outline-none focus-visible:ring-2',
          'focus-visible:ring-ring focus-visible:ring-offset-2',
          'focus-visible:ring-offset-background',
          // Disabled styles
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'disabled:pointer-events-none',
          // Variant and size
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {isLoading ? (
          <span className="spinner spinner-sm" aria-hidden="true" />
        ) : (
          leftIcon && <span className="shrink-0">{leftIcon}</span>
        )}
        <span>{children}</span>
        {!isLoading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button, type ButtonProps, type ButtonVariant, type ButtonSize };
