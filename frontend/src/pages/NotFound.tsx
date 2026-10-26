import React from "react";
import { Link } from "react-router-dom";
import { AlertCircle, ArrowLeft } from "lucide-react";

export const NotFound: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="p-4 bg-rose-50 text-rose-600 rounded-full mb-4">
        <AlertCircle className="h-10 w-10" />
      </div>
      <h1 className="text-3xl font-bold text-slate-900">404 - Page Not Found</h1>
      <p className="mt-2 text-sm text-slate-500 max-w-md">
        The requested resource does not exist on this AICTE portal node.
      </p>
      <Link
        to="/"
        className="mt-6 inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors shadow-sm"
      >
        <ArrowLeft className="h-4 w-4" />
        Return to Dashboard
      </Link>
    </div>
  );
};
