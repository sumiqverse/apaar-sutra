import React from "react";
import { useTranslation } from "react-i18next";
import { Search, RotateCcw, Bookmark } from "lucide-react";

export interface FilterState {
  academicYear: string;
  stateCode: string;
  institutionType: string;
  programLevel: string;
  search: string;
}

interface FilterBarProps {
  filters: FilterState;
  onChange: (updated: Partial<FilterState>) => void;
  onReset: () => void;
  statesList: { code: string; name: string }[];
}

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onChange,
  onReset,
  statesList,
}) => {
  const { t } = useTranslation();

  const handleSavedView = (view: string) => {
    switch (view) {
      case "critical":
        onChange({ institutionType: "", programLevel: "", search: "" });
        break;
      case "autonomous":
        onChange({ institutionType: "AUTONOMOUS", search: "" });
        break;
      case "pg":
        onChange({ programLevel: "PG", search: "" });
        break;
      case "reset":
        onReset();
        break;
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm space-y-3">
      {/* Top Filter Bar Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            id="filter-search"
            value={filters.search}
            onChange={(e) => onChange({ search: e.target.value })}
            placeholder={t("dashboard.filter.search_placeholder", "Search college or AICTE ID...")}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {/* Academic Year */}
        <div>
          <select
            id="filter-year"
            value={filters.academicYear}
            onChange={(e) => onChange({ academicYear: e.target.value })}
            className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="2025-26">AY 2025-26 (Current)</option>
            <option value="2024-25">AY 2024-25</option>
            <option value="2023-24">AY 2023-24</option>
          </select>
        </div>

        {/* State */}
        <div>
          <select
            id="filter-state"
            value={filters.stateCode}
            onChange={(e) => onChange({ stateCode: e.target.value })}
            className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">{t("dashboard.filter.all_states", "All States & UTs")}</option>
            {statesList.map((st) => (
              <option key={st.code} value={st.code}>
                {st.name} ({st.code})
              </option>
            ))}
          </select>
        </div>

        {/* Institution Type */}
        <div>
          <select
            id="filter-type"
            value={filters.institutionType}
            onChange={(e) => onChange({ institutionType: e.target.value })}
            className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">{t("dashboard.filter.all_types", "All Institution Types")}</option>
            <option value="AUTONOMOUS">Autonomous</option>
            <option value="AFFILIATED">Affiliated</option>
            <option value="UNIVERSITY">University</option>
            <option value="STANDALONE_PGDM">Standalone PGDM</option>
          </select>
        </div>

        {/* Program Level */}
        <div>
          <select
            id="filter-level"
            value={filters.programLevel}
            onChange={(e) => onChange({ programLevel: e.target.value })}
            className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">{t("dashboard.filter.all_levels", "All Degree Levels")}</option>
            <option value="UG">Undergraduate (UG)</option>
            <option value="PG">Postgraduate (PG)</option>
            <option value="DIPLOMA">Diploma</option>
            <option value="PHD">Ph.D Research</option>
          </select>
        </div>
      </div>

      {/* Saved Views Strip */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-slate-500 dark:text-slate-400 flex items-center gap-1 font-medium mr-1">
            <Bookmark className="h-3.5 w-3.5 text-brand-500" />
            {t("dashboard.filter.saved_views", "Saved Views:")}
          </span>
          <button
            type="button"
            onClick={() => handleSavedView("reset")}
            className="px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 font-medium transition-colors"
          >
            All National
          </button>
          <button
            type="button"
            onClick={() => handleSavedView("critical")}
            className="px-2.5 py-1 rounded-md bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900/40 font-medium hover:bg-rose-100 transition-colors"
          >
            Critical Risk Watchlist
          </button>
          <button
            type="button"
            onClick={() => handleSavedView("autonomous")}
            className="px-2.5 py-1 rounded-md bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-900/40 font-medium hover:bg-indigo-100 transition-colors"
          >
            Autonomous Tier
          </button>
          <button
            type="button"
            onClick={() => handleSavedView("pg")}
            className="px-2.5 py-1 rounded-md bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-900/40 font-medium hover:bg-emerald-100 transition-colors"
          >
            PG & Masters
          </button>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-1 text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          {t("common.reset", "Reset Filters")}
        </button>
      </div>
    </div>
  );
};
