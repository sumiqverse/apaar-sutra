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
      className="bg-white rounded-[20px] border border-[#E5E5E5] p-6 space-y-4"
    >
      {/* Header and Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-[#F5F5F5] border border-[#E5E5E5] flex items-center justify-center text-black">
              <Building className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-black tracking-[-0.2px]">
                {t("dashboard.leaderboard.title", "Institutional Anomaly & Risk Leaderboard")}
              </h2>
              <span className="font-mono text-[10px] text-black/50 uppercase tracking-[0.54px]">
                Ranked by Isolation Forest ML anomaly risk index • Click row for audit inspection
              </span>
            </div>
          </div>
        </div>

        {/* Export Buttons (Pills) */}
        <div className="flex items-center gap-2 print:hidden">
          <button
            type="button"
            id="export-csv-btn"
            onClick={handleExportCsv}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-full border border-[#E5E5E5] bg-white text-black hover:bg-[#F5F5F5] transition-all cursor-pointer"
          >
            <Download className="h-3.5 w-3.5 text-black" />
            CSV Export
          </button>
          <button
            type="button"
            id="export-pdf-btn"
            onClick={handlePrintPdf}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-full border border-[#E5E5E5] bg-white text-black hover:bg-[#F5F5F5] transition-all cursor-pointer"
          >
            <Printer className="h-3.5 w-3.5 text-black" />
            PDF Report
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-[14px] border border-[#E5E5E5]">
        <table className="w-full text-left text-xs text-black">
          <thead className="bg-[#F5F5F5] text-black font-mono uppercase text-[10px] tracking-[0.54px] border-b border-[#E5E5E5]">
            <tr>
              <th className="py-3 px-3.5 w-12 text-center">Rank</th>
              <th className="py-3 px-3.5">Institution & AICTE ID</th>
              <th className="py-3 px-3.5">State</th>
              <th className="py-3 px-3.5">Type</th>
              <th className="py-3 px-3.5 text-right">Capacity</th>
              <th className="py-3 px-3.5 text-right">Enrolled</th>
              <th className="py-3 px-3.5 text-center">Utilisation</th>
              <th className="py-3 px-3.5 text-center">Risk Score</th>
              <th className="py-3 px-3.5 text-center">Issues</th>
              <th className="py-3 px-3.5 text-center w-20 print:hidden">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E5E5E5]">
            {items.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-8 text-center text-black/40 font-[330]">
                  No institutions found matching the current filters.
                </td>
              </tr>
            ) : (
              items.map((row, idx) => {
                const rank = (page - 1) * pageSize + idx + 1;
                const isOverCap = row.utilisation_pct > 100;

                // Color code for risk score badge (Figma pill badges)
                let riskBadgeClass = "bg-[#D2F8E7] text-black";
                if (row.risk_score >= 80) {
                  riskBadgeClass = "bg-[#FF8577] text-black";
                } else if (row.risk_score >= 60) {
                  riskBadgeClass = "bg-[#FFD6E8] text-black";
                } else if (row.risk_score >= 35) {
                  riskBadgeClass = "bg-[#FFF5EA] text-black border border-[#E5E5E5]";
                }

                return (
                  <tr
                    key={row.id}
                    onClick={() => onSelectInstitution(row.id)}
                    className="hover:bg-[#F9F9F9] cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-3.5 text-center font-mono font-semibold text-black/60">
                      {rank}
                    </td>

                    <td className="py-3.5 px-3.5">
                      <div className="font-semibold text-black truncate max-w-[260px]" title={row.name}>
                        {row.name}
                      </div>
                      <div className="text-[11px] font-mono text-black/50">
                        {row.aicte_id}
                        {row.top_contributing_factor && (
                          <span className="ml-2 text-rose-600 font-sans truncate inline-block max-w-[180px]" title={row.top_contributing_factor}>
                            • {row.top_contributing_factor}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-3.5 px-3.5 whitespace-nowrap">
                      <span className="font-medium text-black">
                        {row.state_code}
                      </span>
                    </td>

                    <td className="py-3.5 px-3.5 whitespace-nowrap">
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-[0.54px] font-medium bg-[#F5F5F5] border border-[#E5E5E5] text-black">
                        {row.institution_type}
                      </span>
                    </td>

                    <td className="py-3.5 px-3.5 text-right font-mono tabular-nums text-black/70">
                      {row.approved_intake.toLocaleString()}
                    </td>

                    <td className="py-3.5 px-3.5 text-right font-mono font-medium text-black tabular-nums">
                      {row.enrolment_count.toLocaleString()}
                    </td>

                    <td className="py-3.5 px-3.5 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <div className="w-16 bg-[#F5F5F5] rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full ${isOverCap ? "bg-rose-500" : "bg-black"}`}
                            style={{ width: `${Math.min(100, row.utilisation_pct)}%` }}
                          />
                        </div>
                        <span className={`text-[11px] font-mono font-semibold tabular-nums ${isOverCap ? "text-rose-600" : "text-black"}`}>
                          {row.utilisation_pct}%
                        </span>
                      </div>
                    </td>

                    <td className="py-3.5 px-3.5 text-center">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold ${riskBadgeClass}`}>
                        {row.risk_score.toFixed(1)}
                      </span>
                    </td>

                    <td className="py-3.5 px-3.5 text-center">
                      {row.open_issues_count > 0 ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-[#FF8577]/30 text-black">
                          <AlertTriangle className="h-3 w-3" />
                          {row.open_issues_count}
                        </span>
                      ) : (
                        <span className="text-black/40 text-xs">-</span>
                      )}
                    </td>

                    <td className="py-3.5 px-3.5 text-center print:hidden">
                      <div className="w-7 h-7 rounded-full bg-[#F5F5F5] border border-[#E5E5E5] flex items-center justify-center text-black hover:bg-black hover:text-white transition-colors mx-auto">
                        <ChevronRight className="h-3.5 w-3.5" />
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex items-center justify-between pt-2 text-xs text-black/60 print:hidden">
        <div className="font-[330]">
          Showing {items.length > 0 ? (page - 1) * pageSize + 1 : 0} to{" "}
          {Math.min(total, page * pageSize)} of {total} institutions
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
            className="p-1.5 rounded-full border border-[#E5E5E5] bg-white text-black disabled:opacity-40 hover:bg-[#F5F5F5] transition-colors cursor-pointer"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="font-mono text-xs font-medium text-black">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
            className="p-1.5 rounded-full border border-[#E5E5E5] bg-white text-black disabled:opacity-40 hover:bg-[#F5F5F5] transition-colors cursor-pointer"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
