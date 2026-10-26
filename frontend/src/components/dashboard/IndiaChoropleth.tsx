import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { INDIA_STATES_PATHS } from "@/assets/india_map_data";
import { Layers } from "lucide-react";

export type ChoroplethMetric = "utilisation" | "violations" | "risk";

export interface StateData {
  state_id: string;
  state_code: string;
  state_name: string;
  intake_utilisation_pct: number;
  violation_count: number;
  risk_score: number;
  risk_level: string;
  institutions_count: number;
  total_enrolments: number;
  approved_intake: number;
}

interface IndiaChoroplethProps {
  data: StateData[];
  selectedStateCode?: string | null;
  onSelectState?: (stateCode: string | null) => void;
}

export const IndiaChoropleth: React.FC<IndiaChoroplethProps> = ({
  data,
  selectedStateCode,
  onSelectState,
}) => {
  const { t } = useTranslation();
  const [activeMetric, setActiveMetric] = useState<ChoroplethMetric>("risk");
  const [hoveredState, setHoveredState] = useState<{
    state: StateData;
    coords: { x: number; y: number };
  } | null>(null);

  // Map state data by code for quick lookup
  const stateDataMap = new Map<string, StateData>();
  for (const item of data) {
    stateDataMap.set(item.state_code, item);
  }

  // Get color for path based on selected metric
  const getStateColor = (code: string) => {
    const item = stateDataMap.get(code);
    if (!item) {
      return "#cbd5e1"; // slate-300 fallback
    }

    if (activeMetric === "risk") {
      const score = item.risk_score;
      if (score >= 80) return "#e11d48"; // rose-600
      if (score >= 60) return "#f97316"; // orange-500
      if (score >= 35) return "#eab308"; // yellow-500
      return "#10b981"; // emerald-500
    }

    if (activeMetric === "violations") {
      const v = item.violation_count;
      if (v > 15) return "#dc2626"; // red-600
      if (v > 5) return "#f59e0b"; // amber-500
      if (v > 0) return "#3b82f6"; // blue-500
      return "#10b981"; // emerald-500
    }

    // "utilisation"
    const u = item.intake_utilisation_pct;
    if (u > 105) return "#ea580c"; // orange-600 (capacity breach)
    if (u >= 85) return "#059669"; // emerald-600 (optimal)
    if (u >= 50) return "#0284c7"; // sky-600
    return "#64748b"; // slate-500 (under-utilized)
  };

  const handleMouseMove = (e: React.MouseEvent, code: string, name: string) => {
    const rect = e.currentTarget.closest("svg")?.getBoundingClientRect();
    if (!rect) return;

    const item = stateDataMap.get(code) || {
      state_id: code,
      state_code: code,
      state_name: name,
      intake_utilisation_pct: 0,
      violation_count: 0,
      risk_score: 0,
      risk_level: "LOW",
      institutions_count: 0,
      total_enrolments: 0,
      approved_intake: 0,
    };

    setHoveredState({
      state: item,
      coords: {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      },
    });
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm relative">
      {/* Header with Title and Metric Switcher */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Layers className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            {t("dashboard.map.title", "Pan-India Institutional Telemetry")}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t("dashboard.map.subtitle", "Interactive state choropleth (offline vector asset)")}
            {selectedStateCode && (
              <span className="ml-2 font-semibold text-brand-600 dark:text-brand-400">
                • Filtered: {selectedStateCode}
              </span>
            )}
          </p>
        </div>

        {/* Metric Toggle Tabs */}
        <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg text-xs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeMetric === "risk"}
            onClick={() => setActiveMetric("risk")}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
              activeMetric === "risk"
                ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            {t("dashboard.map.metric_risk", "Risk Score")}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeMetric === "violations"}
            onClick={() => setActiveMetric("violations")}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
              activeMetric === "violations"
                ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            {t("dashboard.map.metric_violations", "Violations")}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeMetric === "utilisation"}
            onClick={() => setActiveMetric("utilisation")}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
              activeMetric === "utilisation"
                ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            {t("dashboard.map.metric_utilisation", "Intake Utilisation")}
          </button>
        </div>
      </div>

      {/* SVG Map Container */}
      <div className="relative w-full h-[380px] flex items-center justify-center bg-slate-50 dark:bg-slate-950/60 rounded-xl overflow-hidden border border-slate-100 dark:border-slate-800/80">
        <svg
          viewBox="0 0 620 660"
          className="w-full h-full max-h-[370px]"
          aria-label="Map of India state telemetry"
        >
          {INDIA_STATES_PATHS.map((item) => {
            const isSelected = selectedStateCode === item.code;
            const fillColor = getStateColor(item.code);

            return (
              <g key={item.code} className="cursor-pointer transition-all duration-200">
                <path
                  d={item.path}
                  fill={fillColor}
                  fillOpacity={isSelected ? 1.0 : 0.85}
                  stroke={isSelected ? "#0284c7" : "#ffffff"}
                  strokeWidth={isSelected ? 3 : 1.2}
                  className="hover:opacity-100 hover:stroke-slate-900 dark:hover:stroke-white transition-opacity"
                  onClick={() => onSelectState && onSelectState(isSelected ? null : item.code)}
                  onMouseEnter={(e) => handleMouseMove(e, item.code, item.name)}
                  onMouseMove={(e) => handleMouseMove(e, item.code, item.name)}
                  onMouseLeave={() => setHoveredState(null)}
                />
                {/* State Code Label */}
                <text
                  x={item.centroid[0]}
                  y={item.centroid[1]}
                  textAnchor="middle"
                  alignmentBaseline="central"
                  fontSize="9"
                  fontWeight="600"
                  fill="#ffffff"
                  pointerEvents="none"
                  className="drop-shadow-sm select-none"
                >
                  {item.code}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip Popup */}
        {hoveredState && (
          <div
            className="absolute z-20 pointer-events-none bg-slate-900/95 text-white p-3 rounded-lg shadow-xl text-xs backdrop-blur-sm border border-slate-700 min-w-[180px]"
            style={{
              left: `${Math.min(hoveredState.coords.x + 12, 380)}px`,
              top: `${Math.min(hoveredState.coords.y + 12, 280)}px`,
            }}
          >
            <div className="font-bold border-b border-slate-700 pb-1 mb-1.5 flex items-center justify-between">
              <span>{hoveredState.state.state_name}</span>
              <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded font-mono text-slate-300">
                {hoveredState.state.state_code}
              </span>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">Risk Score:</span>
                <span
                  className={`font-semibold ${
                    hoveredState.state.risk_score >= 80
                      ? "text-rose-400"
                      : hoveredState.state.risk_score >= 50
                      ? "text-amber-400"
                      : "text-emerald-400"
                  }`}
                >
                  {hoveredState.state.risk_score.toFixed(1)} / 100 ({hoveredState.state.risk_level})
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Intake Utilisation:</span>
                <span className="font-semibold text-slate-200">
                  {hoveredState.state.intake_utilisation_pct.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Violations:</span>
                <span className="font-semibold text-slate-200">
                  {hoveredState.state.violation_count}
                </span>
              </div>
              <div className="flex justify-between pt-1 border-t border-slate-800 text-[11px] text-slate-400">
                <span>{hoveredState.state.institutions_count} Colleges</span>
                <span>{(hoveredState.state.total_enrolments || 0).toLocaleString()} Students</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Legend Strip */}
      <div className="flex flex-wrap items-center justify-between gap-2 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
        <div className="flex items-center gap-3">
          <span className="font-medium text-slate-700 dark:text-slate-300">
            {activeMetric === "risk"
              ? "ML Risk Severity:"
              : activeMetric === "violations"
              ? "Violation Density:"
              : "Intake Utilisation:"}
          </span>
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm bg-emerald-500" />
            <span className="text-[11px]">Low / Optimal</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm bg-amber-500" />
            <span className="text-[11px]">Moderate</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm bg-rose-600" />
            <span className="text-[11px]">Critical / High Risk</span>
          </div>
        </div>

        {selectedStateCode && (
          <button
            onClick={() => onSelectState && onSelectState(null)}
            className="text-xs text-brand-600 dark:text-brand-400 hover:underline font-medium"
          >
            Clear State Filter ({selectedStateCode})
          </button>
        )}
      </div>
    </div>
  );
};
