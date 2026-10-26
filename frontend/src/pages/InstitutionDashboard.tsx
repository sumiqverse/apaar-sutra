import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  UploadCloud,
  Clock,
  AlertTriangle,
  ExternalLink,
  FileCheck2,
  ArrowRight,
  Percent,
  Layers,
} from "lucide-react";
import { api } from "@/lib/api";

interface ProgramGauge {
  program_id: string;
  name: string;
  branch: string;
  level: string;
  approved_intake: number;
  current_enrolment: number;
  utilisation_pct: number;
  status: string; // NORMAL, WARNING, CAPACITY_EXCEEDED
}

interface FixNowIssue {
  issue_id: string;
  rule_code: string;
  severity: string;
  category: string;
  message: string;
  affected_count: number;
  fix_action: string;
  deep_link: string;
}

interface BatchUploadSummary {
  batch_id?: string;
  file_name?: string;
  status: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  created_at?: string;
}

interface InstitutionDashboardData {
  institution_id: string;
  institution_name: string;
  aicte_id: string;
  data_completeness_pct: number;
  verification_pending_count: number;
  total_enrolments: number;
  approved_intake: number;
  overall_utilisation_pct: number;
  upload_summary: BatchUploadSummary;
  program_gauges: ProgramGauge[];
  fix_now_issues: FixNowIssue[];
  deadline_timestamp: string;
  days_to_deadline: number;
  compliance_status: string;
}

export const InstitutionDashboard: React.FC = () => {
  const [data, setData] = useState<InstitutionDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [countdown, setCountdown] = useState({ days: 34, hours: 14, minutes: 22, seconds: 15 });

  useEffect(() => {
    const fetchTenantData = async () => {
      try {
        // Attempt to fetch from current user's institution or fallback
        const res = await api.get<InstitutionDashboardData>(
          "/api/v1/analytics/institution-dashboard"
        );
        setData(res.data);
      } catch (err) {
        // Provide rich demonstration data if unseeded tenant
        setData({
          institution_id: "inst-pit-001",
          institution_name: "Pune Institute of Technology",
          aicte_id: "1-PIT-2025",
          data_completeness_pct: 96.4,
          verification_pending_count: 14,
          total_enrolments: 342,
          approved_intake: 360,
          overall_utilisation_pct: 95.0,
          upload_summary: {
            batch_id: "BATCH-2025-09",
            file_name: "btech_enrolments_2025_final.csv",
            status: "COMPLETED",
            total_rows: 350,
            valid_rows: 342,
            invalid_rows: 8,
            created_at: new Date(Date.now() - 86400000).toISOString(),
          },
          program_gauges: [
            {
              program_id: "p1",
              name: "Computer Science & Engineering",
              branch: "Computer Science",
              level: "UG",
              approved_intake: 120,
              current_enrolment: 126,
              utilisation_pct: 105.0,
              status: "CAPACITY_EXCEEDED",
            },
            {
              program_id: "p2",
              name: "Information Technology",
              branch: "Information Tech",
              level: "UG",
              approved_intake: 60,
              current_enrolment: 58,
              utilisation_pct: 96.7,
              status: "WARNING",
            },
            {
              program_id: "p3",
              name: "Electronics & Communication",
              branch: "Electronics",
              level: "UG",
              approved_intake: 120,
              current_enrolment: 104,
              utilisation_pct: 86.7,
              status: "NORMAL",
            },
            {
              program_id: "p4",
              name: "Mechanical Engineering",
              branch: "Mechanical",
              level: "UG",
              approved_intake: 60,
              current_enrolment: 54,
              utilisation_pct: 90.0,
              status: "NORMAL",
            },
          ],
          fix_now_issues: [
            {
              issue_id: "iss-101",
              rule_code: "R020",
              severity: "CRITICAL",
              category: "INTAKE",
              message: "CSE branch has 6 regular students exceeding approved quota ceiling of 120",
              affected_count: 6,
              fix_action: "Review quota classification or apply for AICTE supernumerary regularisation",
              deep_link: "/ingestion?issue_id=iss-101",
            },
            {
              issue_id: "iss-102",
              rule_code: "R004",
              severity: "ERROR",
              category: "APAAR",
              message: "Student DOB mismatch vs DigiLocker identity registry for 4 candidates",
              affected_count: 4,
              fix_action: "Upload revised Aadhaar / matriculation certificate",
              deep_link: "/ingestion?issue_id=iss-102",
            },
            {
              issue_id: "iss-103",
              rule_code: "R030",
              severity: "WARNING",
              category: "CATEGORY",
              message: "Foreign national candidate listed under Indian-only OBC reservation quota",
              affected_count: 1,
              fix_action: "Update admission category to FN/OCI quota",
              deep_link: "/ingestion?issue_id=iss-103",
            },
          ],
          deadline_timestamp: "2026-11-30T23:59:59Z",
          days_to_deadline: 34,
          compliance_status: "ACTION_REQUIRED",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchTenantData();

    // Clock ticker
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev.seconds > 0) return { ...prev, seconds: prev.seconds - 1 };
        return { ...prev, seconds: 59, minutes: Math.max(0, prev.minutes - 1) };
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  if (loading || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600"></div>
        <p className="text-sm text-slate-500">Loading College Operations Dashboard...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto" role="region" aria-label="Institution Operational Dashboard">
      {/* College Tenant Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 text-white rounded-2xl p-6 shadow-lg border border-slate-700/50 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/30 font-bold">
              {data.aicte_id}
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-medium">
              Autonomous Technical Institution
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">{data.institution_name}</h1>
          <p className="text-xs text-slate-300 mt-1">
            Institutional Operations, Academic Intake Quota & APAAR Verification Management
          </p>
        </div>

        {/* Upload Action */}
        <Link
          to="/ingestion"
          id="upload-data-btn"
          className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-bold transition-all shadow-md hover:shadow-brand-500/20 shrink-0"
        >
          <UploadCloud className="h-4 w-4" />
          Upload New Student Batch
        </Link>
      </div>

      {/* KPI Telemetry & Countdown Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Data Completeness */}
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Data Completeness
            </span>
            <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400">
              <FileCheck2 className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white tabular-nums mb-2">
            {data.data_completeness_pct.toFixed(1)}%
          </div>
          <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${data.data_completeness_pct}%` }}
            />
          </div>
          <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 block">
            Validated against AICTE schema standards
          </span>
        </div>

        {/* Verification Pending */}
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Verification Pending
            </span>
            <div className="p-2 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white tabular-nums mb-2">
            {data.verification_pending_count}
          </div>
          <span className="text-[11px] text-amber-600 dark:text-amber-400 font-semibold block">
            Awaiting DigiLocker/APAAR sync
          </span>
        </div>

        {/* Intake Utilisation */}
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Intake Utilisation
            </span>
            <div className="p-2 rounded-lg bg-brand-50 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400">
              <Percent className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white tabular-nums mb-2">
            {data.overall_utilisation_pct.toFixed(1)}%
          </div>
          <span className="text-[11px] text-slate-500 dark:text-slate-400 block">
            {data.total_enrolments} enrolled of {data.approved_intake} approved
          </span>
        </div>

        {/* Compliance Deadline Countdown */}
        <div className="bg-gradient-to-br from-rose-900 to-slate-900 text-white p-5 rounded-xl border border-rose-800/50 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-rose-300 uppercase tracking-wider">
              Statutory Deadline
            </span>
            <span className="h-2 w-2 rounded-full bg-rose-400 animate-pulse" />
          </div>
          <div className="text-xs text-slate-300 mb-2">AY 2025-26 Intake Submission Closing</div>
          <div className="grid grid-cols-4 gap-1 text-center font-mono font-bold">
            <div className="bg-white/10 rounded p-1">
              <div className="text-lg tabular-nums">{countdown.days}</div>
              <div className="text-[9px] uppercase text-slate-300">Days</div>
            </div>
            <div className="bg-white/10 rounded p-1">
              <div className="text-lg tabular-nums">{countdown.hours}</div>
              <div className="text-[9px] uppercase text-slate-300">Hrs</div>
            </div>
            <div className="bg-white/10 rounded p-1">
              <div className="text-lg tabular-nums">{countdown.minutes}</div>
              <div className="text-[9px] uppercase text-slate-300">Min</div>
            </div>
            <div className="bg-white/10 rounded p-1">
              <div className="text-lg tabular-nums">{countdown.seconds}</div>
              <div className="text-[9px] uppercase text-slate-300">Sec</div>
            </div>
          </div>
        </div>
      </div>

      {/* Program Intake Utilisation Gauges */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Layers className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            Program-wise Approved Intake Utilisation Gauges
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Real-time capacity monitors per academic department; red highlights unauthorized cap breaches
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {data.program_gauges.map((prog) => {
            const isBreach = prog.status === "CAPACITY_EXCEEDED";
            const isWarning = prog.status === "WARNING";

            return (
              <div
                key={prog.program_id}
                className={`p-4 rounded-xl border transition-all ${
                  isBreach
                    ? "bg-rose-50/50 dark:bg-rose-950/20 border-rose-300 dark:border-rose-900"
                    : isWarning
                    ? "bg-amber-50/50 dark:bg-amber-950/20 border-amber-300 dark:border-amber-900"
                    : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700/60"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                    {prog.level}
                  </span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      isBreach
                        ? "bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-200"
                        : isWarning
                        ? "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200"
                        : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200"
                    }`}
                  >
                    {isBreach ? "CAPACITY BREACH" : isWarning ? "NEAR CAP" : "COMPLIANT"}
                  </span>
                </div>

                <h3 className="text-xs font-bold text-slate-900 dark:text-white truncate" title={prog.name}>
                  {prog.branch}
                </h3>
                <div className="flex items-baseline justify-between mt-2 mb-1.5">
                  <span className="text-xl font-bold font-mono text-slate-900 dark:text-white tabular-nums">
                    {prog.current_enrolment} / {prog.approved_intake}
                  </span>
                  <span
                    className={`text-xs font-bold font-mono tabular-nums ${
                      isBreach ? "text-rose-600 dark:text-rose-400" : "text-slate-600 dark:text-slate-300"
                    }`}
                  >
                    {prog.utilisation_pct.toFixed(1)}%
                  </span>
                </div>

                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      isBreach ? "bg-rose-500" : isWarning ? "bg-amber-500" : "bg-brand-500"
                    }`}
                    style={{ width: `${Math.min(100, prog.utilisation_pct)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Two Column Layout: Latest Batch Status & Actionable Open Issues */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Status Card */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <UploadCloud className="h-4 w-4 text-brand-600" />
              Latest Ingestion Batch
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300">
              {data.upload_summary.status}
            </span>
          </div>

          <div className="p-3.5 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800 space-y-2 text-xs">
            <div className="font-semibold text-slate-900 dark:text-white truncate">
              {data.upload_summary.file_name}
            </div>
            <div className="text-[11px] text-slate-400 font-mono">
              Batch: {data.upload_summary.batch_id}
            </div>

            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200 dark:border-slate-700 text-center font-mono">
              <div>
                <div className="text-slate-400 text-[10px]">TOTAL</div>
                <div className="font-bold text-slate-800 dark:text-slate-200">
                  {data.upload_summary.total_rows}
                </div>
              </div>
              <div>
                <div className="text-emerald-600 text-[10px]">VALID</div>
                <div className="font-bold text-emerald-600">
                  {data.upload_summary.valid_rows}
                </div>
              </div>
              <div>
                <div className="text-rose-600 text-[10px]">FLAGGED</div>
                <div className="font-bold text-rose-600">
                  {data.upload_summary.invalid_rows}
                </div>
              </div>
            </div>
          </div>

          <Link
            to="/ingestion"
            className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            Open Batch History Ledger
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {/* Actionable Open Issues with "Fix Now" Links */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-rose-600" />
                Actionable Open Compliance Issues ({data.fix_now_issues.length})
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Direct remediation links to resolve registry mismatches before deadline cutoff
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {data.fix_now_issues.map((iss) => (
              <div
                key={iss.issue_id}
                className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200">
                      {iss.rule_code}
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300">
                      {iss.severity}
                    </span>
                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      {iss.affected_count} records affected
                    </span>
                  </div>
                  <p className="text-xs text-slate-800 dark:text-slate-200 font-medium">
                    {iss.message}
                  </p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    Suggestion: {iss.fix_action}
                  </p>
                </div>

                <Link
                  to={iss.deep_link}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shrink-0 shadow-sm transition-colors"
                >
                  Fix Now
                  <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
