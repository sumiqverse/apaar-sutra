import React from "react";
import { useTranslation } from "react-i18next";
import {
  Download,
  Printer,
  ChevronRight,
  AlertTriangle,
  Building,
  ChevronLeft,
} from "lucide-react";
import { exportToCsv, exportToPdf } from "@/lib/exportUtils";

export interface LeaderboardRow {
  id: string;
  aicte_id: string;
  name: string;
  state_name: string;
  state_code: string;
  institution_type: string;
  approved_intake: number;
  enrolment_count: number;
  utilisation_pct: number;
  risk_score: number;
  risk_level: string;
  open_issues_count: number;
  critical_issues_count: number;
  top_contributing_factor?: string | null;
  status: string;
}

interface InstitutionLeaderboardProps {
  items: LeaderboardRow[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
  onSelectInstitution: (institutionId: string) => void;
  loading?: boolean;
}

export const InstitutionLeaderboard: React.FC<InstitutionLeaderboardProps> = ({
  items,
  total,
  page,
  pageSize,
  onPageChange,
  onSelectInstitution,
}) => {
  const { t } = useTranslation();
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const handleExportCsv = () => {
    const exportData = items.map((item, idx) => ({
      Rank: (page - 1) * pageSize + idx + 1,
      "AICTE ID": item.aicte_id,
      "Institution Name": item.name,
      State: `${item.state_name} (${item.state_code})`,
      Type: item.institution_type,
      "Approved Intake": item.approved_intake,
      "Enrolled Students": item.enrolment_count,
      "Utilisation %": `${item.utilisation_pct}%`,
      "Risk Score": `${item.risk_score} (${item.risk_level})`,
      "Open Issues": item.open_issues_count,
      "Top Risk Factor": item.top_contributing_factor || "N/A",
    }));
    exportToCsv("AICTE_Institutional_Risk_Leaderboard", exportData);
  };

  const handlePrintPdf = () => {
    exportToPdf("institution-leaderboard-container", "AICTE National Institutional Telemetry Report");
  };

  return (
    <div
      id="institution-leaderboard-container"
      className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4"
    >
      {/* Header and Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Building className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            {t("dashboard.leaderboard.title", "Institutional Anomaly & Risk Leaderboard")}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t(
              "dashboard.leaderboard.subtitle",
              "Ranked by Isolation Forest ML anomaly risk index; click row for deep audit inspection"
            )}
          </p>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center gap-2 print:hidden">
          <button
            type="button"
            id="export-csv-btn"
            onClick={handleExportCsv}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
          >
            <Download className="h-3.5 w-3.5 text-brand-600 dark:text-brand-400" />
            CSV Export
          </button>
          <button
            type="button"
            id="export-pdf-btn"
            onClick={handlePrintPdf}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
          >
            <Printer className="h-3.5 w-3.5 text-slate-600 dark:text-slate-400" />
            PDF Report
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-lg border border-slate-100 dark:border-slate-800">
        <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
          <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-700 dark:text-slate-200 font-semibold border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="py-3 px-3 w-12 text-center">Rank</th>
              <th className="py-3 px-3">Institution & ID</th>
              <th className="py-3 px-3">State</th>
              <th className="py-3 px-3">Type</th>
              <th className="py-3 px-3 text-right">Capacity</th>
              <th className="py-3 px-3 text-right">Enrolled</th>
              <th className="py-3 px-3 text-center">Utilisation</th>
              <th className="py-3 px-3 text-center">Risk Score</th>
              <th className="py-3 px-3 text-center">Issues</th>
              <th className="py-3 px-3 text-center w-20 print:hidden">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {items.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-8 text-center text-slate-400">
                  No institutions found matching the current filters.
                </td>
              </tr>
            ) : (
              items.map((row, idx) => {
                const rank = (page - 1) * pageSize + idx + 1;
                const isOverCap = row.utilisation_pct > 100;

                // Color code for risk score badge
                let riskBadgeClass = "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400";
                if (row.risk_score >= 80) {
                  riskBadgeClass = "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-400";
                } else if (row.risk_score >= 60) {
                  riskBadgeClass = "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950/40 dark:text-orange-400";
                } else if (row.risk_score >= 35) {
                  riskBadgeClass = "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400";
                }

                return (
                  <tr
                    key={row.id}
                    onClick={() => onSelectInstitution(row.id)}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-3 text-center font-mono font-semibold text-slate-500">
                      {rank}
                    </td>

                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-900 dark:text-white truncate max-w-[260px]" title={row.name}>
                        {row.name}
                      </div>
                      <div className="text-[11px] font-mono text-slate-400">
                        {row.aicte_id}
                        {row.top_contributing_factor && (
                          <span className="ml-2 text-rose-600 dark:text-rose-400 font-sans truncate inline-block max-w-[180px]" title={row.top_contributing_factor}>
                            • {row.top_contributing_factor}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-3 px-3 whitespace-nowrap">
                      <span className="font-medium text-slate-800 dark:text-slate-200">
                        {row.state_code}
                      </span>
                    </td>

                    <td className="py-3 px-3 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                        {row.institution_type}
                      </span>
                    </td>

                    <td className="py-3 px-3 text-right font-mono tabular-nums">
                      {row.approved_intake.toLocaleString()}
                    </td>

                    <td className="py-3 px-3 text-right font-mono font-medium text-slate-900 dark:text-white tabular-nums">
                      {row.enrolment_count.toLocaleString()}
                    </td>

                    <td className="py-3 px-3 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <div className="w-16 bg-slate-100 dark:bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full ${isOverCap ? "bg-rose-500" : "bg-brand-500"}`}
                            style={{ width: `${Math.min(100, row.utilisation_pct)}%` }}
                          />
                        </div>
                        <span className={`text-[11px] font-mono font-semibold tabular-nums ${isOverCap ? "text-rose-600 dark:text-rose-400" : ""}`}>
                          {row.utilisation_pct}%
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-mono font-bold border ${riskBadgeClass}`}>
                        {row.risk_score.toFixed(1)}
                      </span>
                    </td>

                    <td className="py-3 px-3 text-center">
                      {row.open_issues_count > 0 ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400">
                          <AlertTriangle className="h-3 w-3" />
                          {row.open_issues_count}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-xs">-</span>
                      )}
                    </td>

                    <td className="py-3 px-3 text-center print:hidden">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectInstitution(row.id);
                        }}
                        className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
                        title="Inspect institutional details"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex items-center justify-between pt-2 text-xs text-slate-500 dark:text-slate-400 print:hidden">
        <div>
          Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to{" "}
          {Math.min(total, page * pageSize)} of {total} institutions
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="font-medium text-slate-700 dark:text-slate-300">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
