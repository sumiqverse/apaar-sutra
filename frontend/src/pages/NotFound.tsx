import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, ArrowLeft, Home, FileQuestion } from "lucide-react";

export const NotFound: React.FC = () => {
  useEffect(() => {
    document.title = "404 - Page Not Found | APAAR-Sutra";
  }, []);

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="flex flex-col items-center justify-center min-h-[70vh] text-center px-4"
    >
      <div className="p-4 bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 rounded-2xl mb-4 border border-rose-200 dark:border-rose-900">
        <FileQuestion className="h-12 w-12" aria-hidden="true" />
      </div>
      <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
        404 - Page Not Found
      </h1>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-md leading-relaxed">
        The requested resource, route, or statutory registry record does not exist on this AICTE portal node.
      </p>
      <div className="mt-6 flex items-center gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none transition shadow-sm"
          aria-label="Return to National AICTE Dashboard"
        >
          <Home className="h-4 w-4" aria-hidden="true" />
          Return to Dashboard
        </Link>
        <button
          onClick={() => window.history.back()}
          className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:outline-none transition"
          aria-label="Go back to previous page"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Go Back
        </button>
      </div>
    </div>
  );
};
export default NotFound;
