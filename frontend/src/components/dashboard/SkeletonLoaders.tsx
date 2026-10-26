import React from "react";

export const KpiStripSkeleton: React.FC = () => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 animate-pulse">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="h-3 w-16 bg-slate-200 dark:bg-slate-700 rounded mb-2"></div>
          <div className="h-7 w-20 bg-slate-200 dark:bg-slate-700 rounded mb-2"></div>
          <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded"></div>
        </div>
      ))}
    </div>
  );
};

export const MapSkeleton: React.FC = () => {
  return (
    <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm h-96 flex flex-col items-center justify-center animate-pulse">
      <div className="h-6 w-48 bg-slate-200 dark:bg-slate-700 rounded mb-4"></div>
      <div className="h-64 w-64 bg-slate-100 dark:bg-slate-800 rounded-full"></div>
    </div>
  );
};

export const TableSkeleton: React.FC = () => {
  return (
    <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm animate-pulse space-y-4">
      <div className="flex justify-between items-center">
        <div className="h-6 w-40 bg-slate-200 dark:bg-slate-700 rounded"></div>
        <div className="h-8 w-24 bg-slate-200 dark:bg-slate-700 rounded"></div>
      </div>
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-10 w-full bg-slate-100 dark:bg-slate-800 rounded"></div>
        ))}
      </div>
    </div>
  );
};
