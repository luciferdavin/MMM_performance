import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

export interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value: number;
}

export function Progress({ className, value, ...props }: ProgressProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn('relative h-2 w-full overflow-hidden rounded-full bg-slate-100', className)}
      {...props}
    >
      <div className="h-full bg-indigo-600 transition-all" style={{ width: `${clamped}%` }} />
    </div>
  );
}
