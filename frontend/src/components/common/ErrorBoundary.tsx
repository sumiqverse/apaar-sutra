import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Copy, Check, Home } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  copied: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      copied: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error("Uncaught application runtime error:", error, errorInfo);
  }

  handleCopyDiagnostic = () => {
    const diagnostic = {
      timestamp: new Date().toISOString(),
      url: window.location.href,
      errorMessage: this.state.error?.message,
      errorStack: this.state.error?.stack,
      componentStack: this.state.errorInfo?.componentStack,
    };
    navigator.clipboard.writeText(JSON.stringify(diagnostic, null, 2));
    this.setState({ copied: true });
    setTimeout(() => this.setState({ copied: false }), 2500);
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          aria-live="assertive"
          className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-6"
        >
          <div className="max-w-xl w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-xl text-center space-y-6">
            <div className="mx-auto w-16 h-16 bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 rounded-2xl flex items-center justify-center border border-rose-200 dark:border-rose-900">
              <AlertTriangle className="w-8 h-8" aria-hidden="true" />
            </div>

            <div className="space-y-2">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                Something went wrong
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto leading-relaxed">
                An unexpected interface error occurred. The statutory database and backend audit logs remain completely secure.
              </p>
            </div>

            {this.state.error && (
              <div className="text-left bg-slate-950 text-slate-300 p-4 rounded-xl text-xs font-mono overflow-x-auto max-h-36 border border-slate-800">
                <div className="text-rose-400 font-semibold mb-1">
                  {this.state.error.name}: {this.state.error.message}
                </div>
                <div className="text-[11px] text-slate-500 leading-normal">
                  {this.state.error.stack?.split("\n").slice(0, 3).join("\n")}
                </div>
              </div>
            )}

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <button
                onClick={this.handleReload}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none transition shadow-sm"
              >
                <RefreshCw className="w-4 h-4" aria-hidden="true" />
                Reload Platform
              </button>

              <button
                onClick={this.handleCopyDiagnostic}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 rounded-xl focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none transition"
              >
                {this.state.copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                {this.state.copied ? "Copied Diagnostics" : "Copy Error Diagnostics"}
              </button>

              <a
                href="/"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white rounded-xl transition"
              >
                <Home className="w-4 h-4" />
                Home
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
export default ErrorBoundary;
