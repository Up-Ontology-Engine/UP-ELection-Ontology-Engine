"use client";

/**
 * ErrorBoundary — catches React render errors and shows a fallback UI.
 *
 * Usage:
 *   <ErrorBoundary label="Booth Map">
 *     <LeafletMap ... />
 *   </ErrorBoundary>
 *
 * The label appears in the error card so users know which section failed.
 * Errors are also logged to console.error for monitoring pickup.
 */

import React, { Component, type ReactNode } from "react";

interface Props {
  children:  ReactNode;
  label?:    string;       // section name shown in fallback card
  fallback?: ReactNode;    // custom fallback (overrides default card)
}

interface State {
  hasError:   boolean;
  errorMsg:   string;
  errorStack: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMsg: "", errorStack: "" };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError:   true,
      errorMsg:   error?.message ?? "Unknown render error",
      errorStack: error?.stack   ?? "",
    };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(
      `[ErrorBoundary] "${this.props.label ?? "Section"}" crashed:`,
      error,
      info.componentStack,
    );
  }

  handleRetry = () => {
    this.setState({ hasError: false, errorMsg: "", errorStack: "" });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback;
    }

    const label = this.props.label ?? "This section";

    return (
      <div
        role="alert"
        style={{
          display:       "flex",
          flexDirection: "column",
          alignItems:    "center",
          justifyContent:"center",
          gap:           "12px",
          padding:       "32px 24px",
          background:    "var(--bg-surface, #1e293b)",
          border:        "1px solid var(--border, #334155)",
          borderRadius:  "2px",
          minHeight:     "140px",
          textAlign:     "center",
        }}
      >
        {/* Icon */}
        <span style={{ fontSize: "28px", lineHeight: 1 }}>⚠️</span>

        {/* Title */}
        <p
          style={{
            margin:     0,
            fontWeight: 600,
            fontSize:   "13px",
            color:      "var(--text-1, #f1f5f9)",
          }}
        >
          {label} failed to render
        </p>

        {/* Error message */}
        <p
          style={{
            margin:   0,
            fontSize: "11px",
            color:    "var(--text-3, #94a3b8)",
            maxWidth: "380px",
          }}
        >
          {this.state.errorMsg}
        </p>

        {/* Retry button */}
        <button
          onClick={this.handleRetry}
          style={{
            marginTop:     "4px",
            padding:       "6px 18px",
            background:    "var(--saffron-subtle, rgba(249,115,22,0.1))",
            border:        "1px solid var(--saffron, #f97316)",
            borderRadius:  "2px",
            color:         "var(--saffron, #f97316)",
            fontSize:      "11px",
            fontWeight:    600,
            cursor:        "pointer",
            letterSpacing: "0.04em",
          }}
        >
          RETRY
        </button>
      </div>
    );
  }
}

/**
 * withErrorBoundary — HOC to wrap any component with an error boundary.
 *
 * Usage:
 *   const SafeLeafletMap = withErrorBoundary(LeafletMap, "Booth Map");
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  label: string,
): React.FC<P> {
  const Wrapped: React.FC<P> = (props) => (
    <ErrorBoundary label={label}>
      <Component {...props} />
    </ErrorBoundary>
  );
  Wrapped.displayName = `WithErrorBoundary(${label})`;
  return Wrapped;
}
