/**
 * Status Indicator Components
 *
 * Visual indicators for connection status, with accessibility support.
 */

import { type HTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

type StatusType = 'connected' | 'disconnected' | 'pending';

interface StatusDotProps extends HTMLAttributes<HTMLSpanElement> {
  status: StatusType;
  size?: 'sm' | 'md' | 'lg';
}

const dotSizes = {
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
  lg: 'w-3 h-3',
};

const statusStyles: Record<StatusType, string> = {
  connected: 'bg-success shadow-glow-success',
  disconnected: 'bg-danger shadow-glow-danger',
  pending: 'bg-warning animate-pulse',
};

const statusLabels: Record<StatusType, string> = {
  connected: 'Connected',
  disconnected: 'Disconnected',
  pending: 'Connecting',
};

function StatusDot({ status, size = 'md', className, ...props }: StatusDotProps) {
  return (
    <span
      className={cn(
        'rounded-full',
        'transition-all duration-300',
        dotSizes[size],
        statusStyles[status],
        className
      )}
      role="status"
      aria-label={statusLabels[status]}
      {...props}
    />
  );
}

interface StatusBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  status: StatusType;
  label?: string;
}

function StatusBadge({ status, label, className, ...props }: StatusBadgeProps) {
  const displayLabel = label || statusLabels[status];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-2',
        'px-3 py-1 rounded-full',
        'text-xs font-medium',
        status === 'connected' && 'bg-success/10 text-success border border-success/20',
        status === 'disconnected' && 'bg-danger/10 text-danger border border-danger/20',
        status === 'pending' && 'bg-warning/10 text-warning border border-warning/20',
        className
      )}
      role="status"
      {...props}
    >
      <StatusDot status={status} size="sm" />
      {displayLabel}
    </span>
  );
}

interface ConnectionStatusProps extends HTMLAttributes<HTMLDivElement> {
  isConnected: boolean;
  isLoading?: boolean;
}

function ConnectionStatus({
  isConnected,
  isLoading = false,
  className,
  ...props
}: ConnectionStatusProps) {
  const status: StatusType = isLoading
    ? 'pending'
    : isConnected
      ? 'connected'
      : 'disconnected';

  return (
    <div
      className={cn('flex items-center gap-2', className)}
      role="status"
      aria-live="polite"
      {...props}
    >
      <StatusDot status={status} />
      <span className="text-sm text-muted-foreground">
        {statusLabels[status]}
      </span>
    </div>
  );
}

export {
  StatusDot,
  StatusBadge,
  ConnectionStatus,
  type StatusType,
  type StatusDotProps,
  type StatusBadgeProps,
  type ConnectionStatusProps,
};
