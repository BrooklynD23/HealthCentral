/**
 * Route error boundary (UI-ROUTES, HC-UIRT-001).
 *
 * A page that throws while rendering shows this fallback inside the layout
 * instead of a blank screen. The thrown message is never shown or logged: it
 * can carry patient data. App.tsx keys the boundary by path, so navigating
 * away from a broken page clears the fallback.
 */

import { Component, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { buttonVariants } from './ui/Button';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    // Log the error name only. The message can carry patient data.
    console.error(`Route render failed: ${error.name}`);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div role="alert" className="max-w-xl mx-auto p-8 space-y-4">
          <h2 className="font-display text-2xl text-ink">This page hit a problem</h2>
          <p className="text-ink-secondary">
            Choose another page from the menu, or go to your documents.
          </p>
          <Link to="/inbox" className={buttonVariants({ variant: 'primary' })}>
            Go to Documents
          </Link>
        </div>
      );
    }
    return this.props.children;
  }
}
