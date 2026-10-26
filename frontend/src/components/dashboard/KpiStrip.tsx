import React from "react";
import { useTranslation } from "react-i18next";
import {
  Building2,
  Users,
  Percent,
  AlertTriangle,
  Copy,
  CheckCircle2,
} from "lucide-react";

export interface KpiData {
  institutions_reporting_pct: number;
  total_enrolments: number;
  intake_utilisation_pct: number;
  open_critical_alerts: number;
  duplicates_detected: number;
  verified_records_pct: number;
  total_institutions?: number;
  reporting_institutions?: number;
  total_approved_intake?: number;
}

interface KpiStripProps {
  data: KpiData;
  loading?: boolean;
}

export const KpiStrip: React.FC<KpiStripProps> = ({ data }) => {
  const { t } = useTranslation();

  const cards = [
    {
      id: "kpi-reporting",
      label: t("dashboard.kpi.reporting", "Institutions Reporting"),
      value: `${data.institutions_reporting_pct.toFixed(1)}%`,
      subtext: `${data.reporting_institutions || 0} / ${data.total_institutions || 0} active`,
      icon: Building2,
      color: "text-blue-600 dark:text-blue-400",
      bg: "bg-blue-50 dark:bg-blue-950/40",
      border: "border-blue-200 dark:border-blue-900/40",
      progress: data.institutions_reporting_pct,
      progressColor: "bg-blue-600",
    },
    {
      id: "kpi-enrolments",
      label: t("dashboard.kpi.enrolments", "Total Enrolments"),
      value: (data.total_enrolments || 0).toLocaleString(),
      subtext: "Verified Academic Year 2025-26",
      icon: Users,
      color: "text-indigo-600 dark:text-indigo-400",
      bg: "bg-indigo-50 dark:bg-indigo-950/40",
      border: "border-indigo-200 dark:border-indigo-900/40",
      progress: Math.min(100, ((data.total_enrolments || 0) / 100000) * 100),
      progressColor: "bg-indigo-600",
    },
    {
      id: "kpi-utilisation",
      label: t("dashboard.kpi.utilisation", "Intake Utilisation"),
      value: `${data.intake_utilisation_pct.toFixed(1)}%`,
      subtext: `${data.total_approved_intake ? (data.total_approved_intake).toLocaleString() : "Cap"} approved seats`,
      icon: Percent,
      color: data.intake_utilisation_pct > 100 ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400",
      bg: data.intake_utilisation_pct > 100 ? "bg-amber-50 dark:bg-amber-950/40" : "bg-emerald-50 dark:bg-emerald-950/40",
      border: data.intake_utilisation_pct > 100 ? "border-amber-200 dark:border-amber-900/40" : "border-emerald-200 dark:border-emerald-900/40",
      progress: Math.min(100, data.intake_utilisation_pct),
      progressColor: data.intake_utilisation_pct > 100 ? "bg-amber-500" : "bg-emerald-600",
    },
    {
      id: "kpi-alerts",
      label: t("dashboard.kpi.alerts", "Critical Alerts"),
      value: (data.open_critical_alerts || 0).toString(),
      subtext: "Immediate action required",
      icon: AlertTriangle,
      color: data.open_critical_alerts > 0 ? "text-rose-600 dark:text-rose-400" : "text-slate-600 dark:text-slate-400",
      bg: data.open_critical_alerts > 0 ? "bg-rose-50 dark:bg-rose-950/40" : "bg-slate-50 dark:bg-slate-800/40",
      border: data.open_critical_alerts > 0 ? "border-rose-200 dark:border-rose-900/40" : "border-slate-200 dark:border-slate-700",
      progress: Math.min(100, (data.open_critical_alerts || 0) * 10),
      progressColor: "bg-rose-600",
    },
    {
      id: "kpi-duplicates",
      label: t("dashboard.kpi.duplicates", "Duplicates Detected"),
      value: (data.duplicates_detected || 0).toString(),
      subtext: "Cross-institution / same ID",
      icon: Copy,
      color: "text-amber-600 dark:text-amber-400",
      bg: "bg-amber-50 dark:bg-amber-950/40",
      border: "border-amber-200 dark:border-amber-900/40",
      progress: Math.min(100, (data.duplicates_detected || 0) * 5),
      progressColor: "bg-amber-500",
    },
    {
      id: "kpi-verified",
      label: t("dashboard.kpi.verified", "Verified Records"),
      value: `${data.verified_records_pct.toFixed(1)}%`,
      subtext: "APAAR / DigiLocker authenticated",
      icon: CheckCircle2,
      color: "text-teal-600 dark:text-teal-400",
      bg: "bg-teal-50 dark:bg-teal-950/40",
      border: "border-teal-200 dark:border-teal-900/40",
      progress: data.verified_records_pct,
      progressColor: "bg-teal-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" role="region" aria-label="Key Performance Indicators">
      {cards.map((card) => {
        const IconComponent = card.icon;
        return (
          <div
            key={card.id}
            id={card.id}
            className={`p-4 rounded-xl border bg-white dark:bg-slate-900 ${card.border} shadow-sm hover:shadow-md transition-shadow relative overflow-hidden`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400 truncate max-w-[110px]" title={card.label}>
                {card.label}
              </span>
              <div className={`p-1.5 rounded-lg ${card.bg} ${card.color}`}>
                <IconComponent className="h-4 w-4" />
              </div>
            </div>

            <div className="flex items-baseline gap-1.5 mb-1.5">
              <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white tabular-nums">
                {card.value}
              </span>
            </div>

            <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-1.5 mb-2 overflow-hidden">
              <div
                className={`h-1.5 rounded-full transition-all duration-500 ${card.progressColor}`}
                style={{ width: `${Math.max(4, Math.min(100, card.progress))}%` }}
              />
            </div>

            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
              {card.subtext}
            </p>
          </div>
        );
      })}
    </div>
  );
};
