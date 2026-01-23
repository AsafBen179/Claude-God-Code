/**
 * Card Component
 *
 * Glassmorphism card with multiple variants for the God Mode aesthetic.
 */

import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import { cn } from '../../lib/utils';

type CardVariant = 'default' | 'elevated' | 'interactive' | 'glow';
type CardPadding = 'none' | 'sm' | 'md' | 'lg';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  padding?: CardPadding;
}

const variantStyles: Record<CardVariant, string> = {
  default: cn(
    'bg-card/80 backdrop-blur-md',
    'border border-border/50',
    'shadow-lg shadow-black/10'
  ),
  elevated: cn(
    'bg-card/90 backdrop-blur-lg',
    'border border-border/30',
    'shadow-xl shadow-black/20'
  ),
  interactive: cn(
    'bg-card/80 backdrop-blur-md',
    'border border-border/50',
    'shadow-lg shadow-black/10',
    'cursor-pointer',
    'hover:bg-card hover:border-border hover:shadow-xl',
    'active:scale-[0.99]'
  ),
  glow: cn(
    'bg-card/80 backdrop-blur-md',
    'border border-border/50',
    'shadow-lg shadow-black/10',
    'relative overflow-hidden',
    'before:absolute before:inset-0 before:opacity-0',
    'before:bg-gradient-to-r before:from-primary/10 before:via-accent/10 before:to-primary/10',
    'before:transition-opacity before:duration-300',
    'hover:before:opacity-100'
  ),
};

const paddingStyles: Record<CardPadding, string> = {
  none: 'p-0',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', padding = 'md', ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-xl',
        'transition-all duration-200',
        variantStyles[variant],
        paddingStyles[padding],
        className
      )}
      {...props}
    />
  )
);

Card.displayName = 'Card';

interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {}

const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('space-y-1.5', className)}
      {...props}
    />
  )
);

CardHeader.displayName = 'CardHeader';

interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  as?: 'h1' | 'h2' | 'h3' | 'h4';
}

const CardTitle = forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ className, as: Component = 'h3', ...props }, ref) => (
    <Component
      ref={ref}
      className={cn(
        'text-lg font-semibold leading-tight tracking-tight',
        'text-foreground',
        className
      )}
      {...props}
    />
  )
);

CardTitle.displayName = 'CardTitle';

interface CardDescriptionProps extends HTMLAttributes<HTMLParagraphElement> {}

const CardDescription = forwardRef<HTMLParagraphElement, CardDescriptionProps>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn('text-sm text-muted-foreground', className)}
      {...props}
    />
  )
);

CardDescription.displayName = 'CardDescription';

interface CardContentProps extends HTMLAttributes<HTMLDivElement> {}

const CardContent = forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('pt-4', className)} {...props} />
  )
);

CardContent.displayName = 'CardContent';

interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {}

const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-center pt-4', className)}
      {...props}
    />
  )
);

CardFooter.displayName = 'CardFooter';

export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  type CardProps,
  type CardVariant,
  type CardPadding,
};
