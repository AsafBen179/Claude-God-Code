/**
 * Logo Component
 *
 * Claude God Code branding with the distinctive icon and wordmark.
 */

import { type HTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

interface LogoIconProps extends HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  animated?: boolean;
}

const iconSizes = {
  sm: 'w-8 h-8 text-base',
  md: 'w-10 h-10 text-lg',
  lg: 'w-12 h-12 text-xl',
  xl: 'w-16 h-16 text-2xl',
};

function LogoIcon({ size = 'md', animated = false, className, ...props }: LogoIconProps) {
  return (
    <div
      className={cn(
        'rounded-xl',
        'bg-gradient-to-br from-primary via-primary to-accent',
        'flex items-center justify-center',
        'font-bold text-primary-foreground',
        'shadow-lg shadow-primary/30',
        animated && 'animate-glow',
        iconSizes[size],
        className
      )}
      aria-hidden="true"
      {...props}
    >
      C
    </div>
  );
}

interface LogoWordmarkProps extends HTMLAttributes<HTMLDivElement> {
  showTagline?: boolean;
}

function LogoWordmark({ showTagline = true, className, ...props }: LogoWordmarkProps) {
  return (
    <div className={cn('flex flex-col', className)} {...props}>
      <span className="text-xl font-semibold text-gradient leading-tight">
        Claude God Code
      </span>
      {showTagline && (
        <span className="text-xs text-muted-foreground">
          Autonomous Excellence
        </span>
      )}
    </div>
  );
}

interface LogoProps extends HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg';
  showTagline?: boolean;
  iconOnly?: boolean;
  animated?: boolean;
}

function Logo({
  size = 'md',
  showTagline = true,
  iconOnly = false,
  animated = false,
  className,
  ...props
}: LogoProps) {
  const iconSize = size === 'sm' ? 'sm' : size === 'lg' ? 'lg' : 'md';

  return (
    <div
      className={cn('flex items-center gap-3', className)}
      {...props}
    >
      <LogoIcon size={iconSize} animated={animated} />
      {!iconOnly && <LogoWordmark showTagline={showTagline && size !== 'sm'} />}
    </div>
  );
}

export { Logo, LogoIcon, LogoWordmark, type LogoProps, type LogoIconProps };
