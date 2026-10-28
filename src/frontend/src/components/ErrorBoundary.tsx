/**
 * Route error boundary (UI-ROUTES, HC-UIRT-001).
 *
 * A page that throws while rendering shows this fallback inside the layout
 * instead of a blank screen. The fallback never renders the thrown message,
 * because the message can carry patient data. React itself still logs the
 * thrown error to the browser console, with its message in production, so the
 * message is kept off the page but is not kept out of the console.
 *
 * App.tsx keys the boundary by path, so navigating to another page clears the
 * fallback. The Documents link also clears it, because it can point at the page
 * the user is already on. A chunk that failed to load is not retried by a click
 * (React.lazy keeps the failure), so the Reload action is the way back for it.
 */

import { Component, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Button, buttonVariants } from './ui/Button';

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
    // Adds a one-line note. React logs the error object itself either way.
    console.error(`Route render failed: ${error.name}`);
  }

  private clearError = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div role="alert" className="max-w-xl mx-auto p-8 space-y-4">
          <h2 className="font-display text-2xl text-ink">This page hit a problem</h2>
          <p className="text-ink-secondary">
            Reload the page, or go to your documents.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/inbox" onClick={this.clearError} className={buttonVariants({ variant: 'primary' })}>
              Go to Documents
            </Link>
            <Button variant="secondary" onClick={() => window.location.reload()}>
              Reload page
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
