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
    <div className="bg-white rounded-[20px] border border-[#E5E5E5] p-5 shadow-none space-y-4">
      {/* Top Filter Bar Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-black/40" />
          <input
            type="text"
            id="filter-search"
            value={filters.search}
            onChange={(e) => onChange({ search: e.target.value })}
            placeholder={t("dashboard.filter.search_placeholder", "Search college or AICTE ID...")}
            className="w-full pl-10 pr-3.5 py-2.5 text-xs rounded-[10px] border border-[#E5E5E5] bg-white text-black placeholder-black/40 focus:outline-none focus:border-black transition-colors"
          />
        </div>

        {/* Academic Year */}
        <div>
          <select
            id="filter-year"
            value={filters.academicYear}
            onChange={(e) => onChange({ academicYear: e.target.value })}
            className="w-full px-3.5 py-2.5 text-xs rounded-[10px] border border-[#E5E5E5] bg-white text-black focus:outline-none focus:border-black transition-colors"
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
            className="w-full px-3.5 py-2.5 text-xs rounded-[10px] border border-[#E5E5E5] bg-white text-black focus:outline-none focus:border-black transition-colors"
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
            className="w-full px-3.5 py-2.5 text-xs rounded-[10px] border border-[#E5E5E5] bg-white text-black focus:outline-none focus:border-black transition-colors"
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
            className="w-full px-3.5 py-2.5 text-xs rounded-[10px] border border-[#E5E5E5] bg-white text-black focus:outline-none focus:border-black transition-colors"
          >
            <option value="">{t("dashboard.filter.all_levels", "All Degree Levels")}</option>
            <option value="UG">Undergraduate (UG)</option>
            <option value="PG">Postgraduate (PG)</option>
            <option value="DIPLOMA">Diploma</option>
            <option value="PHD">Ph.D Research</option>
          </select>
        </div>
      </div>

      {/* Saved Views Pill Toggles Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#E5E5E5] text-xs">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.54px] text-black/50 mr-1 flex items-center gap-1.5">
            <Bookmark className="h-3.5 w-3.5 text-black" />
            {t("dashboard.filter.saved_views", "Saved Views:")}
          </span>
          <button
            type="button"
            onClick={() => handleSavedView("reset")}
            className={`px-3.5 py-1.5 rounded-full font-medium transition-all cursor-pointer ${
              !filters.institutionType && !filters.programLevel && !filters.search
                ? "bg-black text-white"
                : "bg-white text-black border border-[#E5E5E5] hover:bg-[#F5F5F5]"
            }`}
          >
            All National
          </button>
          <button
            type="button"
            onClick={() => handleSavedView("critical")}
            className="px-3.5 py-1.5 rounded-full bg-white text-black border border-[#E5E5E5] hover:bg-[#F5F5F5] font-medium transition-all cursor-pointer"
          >
            Critical Risk Watchlist
          </button>
          <button
            type="button"
            onClick={() => handleSavedView("autonomous")}
            className={`px-3.5 py-1.5 rounded-full font-medium transition-all cursor-pointer ${
              filters.institutionType === "AUTONOMOUS"
                ? "bg-black text-white"
                : "bg-white text-black border border-[#E5E5E5] hover:bg-[#F5F5F5]"
            }`}
          >
            Autonomous Tier
          </button>
          <button
            type="button"
            onClick={() => handleSavedView("pg")}
            className={`px-3.5 py-1.5 rounded-full font-medium transition-all cursor-pointer ${
              filters.programLevel === "PG"
                ? "bg-black text-white"
                : "bg-white text-black border border-[#E5E5E5] hover:bg-[#F5F5F5]"
            }`}
          >
            PG & Masters
          </button>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-black/60 hover:text-black hover:bg-[#F5F5F5] transition-colors cursor-pointer"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span className="font-medium">{t("common.reset", "Reset Filters")}</span>
        </button>
      </div>
    </div>
  );
};
