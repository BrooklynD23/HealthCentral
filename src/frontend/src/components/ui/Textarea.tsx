/**
 * Textarea (UI-PRIM-CONTROLS): the same field contract as Input. The label is
 * associated by id, the error sets aria-invalid only while it is present, and
 * the error and hint are linked with aria-describedby.
 */

import * as React from 'react';
import { cn } from '@/utils/cn';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    const generatedId = React.useId();
    const textareaId = id || generatedId;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={textareaId}
            className="block text-sm font-medium text-ink mb-1.5"
          >
            {label}
          </label>
        )}
        <textarea
          id={textareaId}
          className={cn(
            'flex min-h-[88px] w-full rounded-xl border bg-white px-4 py-2',
            'text-ink placeholder:text-ink-tertiary',
            'transition-colors duration-200',
            'focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:border-accent',
            'disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-surface-muted',
            error
              ? 'border-status-critical focus-visible:ring-status-critical focus-visible:border-status-critical'
              : 'border-[var(--line-strong)]',
            className
          )}
          ref={ref}
          aria-invalid={error ? true : undefined}
          aria-describedby={
            error ? `${textareaId}-error` : hint ? `${textareaId}-hint` : undefined
          }
          {...props}
        />
        {error && (
          <p
            id={`${textareaId}-error`}
            className="mt-1.5 text-sm text-status-critical"
            role="alert"
          >
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={`${textareaId}-hint`} className="mt-1.5 text-sm text-ink-tertiary">
            {hint}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

export { Textarea };
