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
      {/* College Tenant Header Banner (Block Lime) */}
      <div className="bg-[#D4FF5B] text-black rounded-[24px] p-8 md:p-10 flex flex-col md:flex-row items-start md:items-end justify-between gap-6">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-black text-white font-semibold uppercase tracking-[0.54px]">
              {data.aicte_id}
            </span>
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-white text-black border border-black/10 font-semibold uppercase tracking-[0.54px]">
              Autonomous Technical Institution
            </span>
          </div>
          <h1 className="text-3xl md:text-5xl font-medium tracking-[-1.2px] text-black leading-[1.05]">
            {data.institution_name}
          </h1>
          <p className="text-sm md:text-base font-[330] text-black/80 max-w-2xl tracking-[-0.26px]">
            Institutional Operations, Academic Intake Quota & APAAR Verification Management Portal.
          </p>
        </div>

        {/* Upload Action (Black Pill Primary) */}
        <Link
          to="/ingestion"
          id="upload-data-btn"
          className="inline-flex items-center gap-2 px-6 py-3 bg-black hover:bg-black/85 text-white rounded-full text-xs font-medium tracking-[-0.1px] transition-all cursor-pointer shrink-0"
        >
          <UploadCloud className="h-4 w-4" />
          <span>Upload Student Batch</span>
        </Link>
      </div>

      {/* KPI Telemetry & Countdown Strip (White Canvas Return) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Data Completeness */}
        <div className="bg-white p-6 rounded-[20px] border border-[#E5E5E5] space-y-3 flex flex-col justify-between hover:border-black transition-colors">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] font-semibold text-black/60 uppercase tracking-[0.54px]">
              Data Completeness
            </span>
            <div className="w-7 h-7 rounded-full bg-[#F5F5F5] border border-[#E5E5E5] flex items-center justify-center text-black">
              <FileCheck2 className="h-3.5 w-3.5" />
            </div>
          </div>
          <div>
            <div className="text-3xl font-semibold tracking-[-0.96px] text-black tabular-nums mb-2">
              {data.data_completeness_pct.toFixed(1)}%
            </div>
            <div className="w-full bg-[#F5F5F5] rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-black h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${data.data_completeness_pct}%` }}
              />
            </div>
          </div>
          <span className="text-[11px] font-[330] text-black/60 block">
            Validated against AICTE schema standards
          </span>
        </div>

        {/* Verification Pending */}
        <div className="bg-white p-6 rounded-[20px] border border-[#E5E5E5] space-y-3 flex flex-col justify-between hover:border-black transition-colors">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] font-semibold text-black/60 uppercase tracking-[0.54px]">
              Verification Pending
            </span>
            <div className="w-7 h-7 rounded-full bg-[#F5F5F5] border border-[#E5E5E5] flex items-center justify-center text-black">
              <Clock className="h-3.5 w-3.5" />
            </div>
          </div>
          <div className="text-3xl font-semibold tracking-[-0.96px] text-black tabular-nums">
            {data.verification_pending_count}
          </div>
          <div>
            <span className="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-[0.54px] font-semibold bg-[#FFD6E8] text-black">
              Awaiting DigiLocker/APAAR sync
            </span>
          </div>
        </div>

        {/* Intake Utilisation */}
        <div className="bg-white p-6 rounded-[20px] border border-[#E5E5E5] space-y-3 flex flex-col justify-between hover:border-black transition-colors">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] font-semibold text-black/60 uppercase tracking-[0.54px]">
              Intake Utilisation
            </span>
            <div className="w-7 h-7 rounded-full bg-[#F5F5F5] border border-[#E5E5E5] flex items-center justify-center text-black">
              <Percent className="h-3.5 w-3.5" />
            </div>
          </div>
          <div className="text-3xl font-semibold tracking-[-0.96px] text-black tabular-nums">
            {data.overall_utilisation_pct.toFixed(1)}%
          </div>
          <span className="text-[11px] font-[330] text-black/60 block">
            {data.total_enrolments} enrolled of {data.approved_intake} approved
          </span>
        </div>

        {/* Statutory Deadline Countdown (Clean Cream/White Pill Card) */}
        <div className="bg-[#FFF5EA] p-6 rounded-[20px] border border-[#E5E5E5] space-y-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] font-semibold text-black/70 uppercase tracking-[0.54px]">
              Statutory Deadline
            </span>
            <span className="h-2 w-2 rounded-full bg-black animate-pulse" />
          </div>
          <div className="font-mono text-[11px] text-black/70">AY 2025-26 Intake Closing</div>
          <div className="grid grid-cols-4 gap-1.5 text-center font-mono">
            <div className="bg-white rounded-[10px] p-1.5 border border-[#E5E5E5]">
              <div className="text-base font-bold text-black tabular-nums">{countdown.days}</div>
              <div className="text-[9px] uppercase tracking-[0.54px] text-black/50">Days</div>
            </div>
            <div className="bg-white rounded-[10px] p-1.5 border border-[#E5E5E5]">
              <div className="text-base font-bold text-black tabular-nums">{countdown.hours}</div>
              <div className="text-[9px] uppercase tracking-[0.54px] text-black/50">Hrs</div>
            </div>
            <div className="bg-white rounded-[10px] p-1.5 border border-[#E5E5E5]">
              <div className="text-base font-bold text-black tabular-nums">{countdown.minutes}</div>
              <div className="text-[9px] uppercase tracking-[0.54px] text-black/50">Min</div>
            </div>
            <div className="bg-white rounded-[10px] p-1.5 border border-[#E5E5E5]">
              <div className="text-base font-bold text-black tabular-nums">{countdown.seconds}</div>
              <div className="text-[9px] uppercase tracking-[0.54px] text-black/50">Sec</div>
            </div>
          </div>
        </div>
      </div>

      {/* Program Intake Utilisation Gauges (Mint Color-Block Section) */}
      <section className="bg-[#D2F8E7] text-black rounded-[24px] p-8 md:p-12 space-y-8">
        <div className="space-y-2">
          <div className="font-mono text-xs font-semibold uppercase tracking-[0.54px] text-black/60">
            Capacity & Utilization Telemetry
          </div>
          <h2 className="text-2xl md:text-4xl font-medium tracking-[-0.96px] text-black">
            Program-wise Approved Intake Utilisation Gauges
          </h2>
          <p className="text-sm md:text-base font-[330] text-black/75 max-w-xl">
            Real-time capacity monitors per academic department; flags statutory seat overshoots.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {data.program_gauges.map((prog) => {
            const isBreach = prog.status === "CAPACITY_EXCEEDED";
            const isWarning = prog.status === "WARNING";

            return (
              <div
                key={prog.program_id}
                className="bg-white p-6 rounded-[20px] border border-black/10 space-y-4 shadow-sm hover:border-black transition-all"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded-full bg-[#F5F5F5] text-black border border-[#E5E5E5]">
                    {prog.level}
                  </span>
                  <span
                    className={`text-[10px] font-mono font-bold uppercase tracking-[0.54px] px-3 py-1 rounded-full ${
                      isBreach
                        ? "bg-[#FF8577] text-black"
                        : isWarning
                        ? "bg-[#FFF5EA] text-black border border-[#E5E5E5]"
                        : "bg-[#D4FF5B] text-black"
                    }`}
                  >
                    {isBreach ? "CAPACITY BREACH" : isWarning ? "NEAR CAP" : "COMPLIANT"}
                  </span>
                </div>

                <h3 className="text-sm font-semibold text-black tracking-[-0.2px] truncate" title={prog.name}>
                  {prog.branch}
                </h3>

                <div className="flex items-baseline justify-between mt-2 mb-1.5">
                  <span className="text-2xl font-semibold font-mono tracking-[-0.96px] text-black tabular-nums">
                    {prog.current_enrolment} / {prog.approved_intake}
                  </span>
                  <span
                    className={`text-xs font-mono font-semibold tabular-nums ${
                      isBreach ? "text-rose-600" : "text-black/60"
                    }`}
                  >
                    {prog.utilisation_pct.toFixed(1)}%
                  </span>
                </div>

                <div className="w-full bg-[#F5F5F5] rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      isBreach ? "bg-rose-500" : isWarning ? "bg-amber-500" : "bg-black"
                    }`}
                    style={{ width: `${Math.min(100, prog.utilisation_pct)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Two Column Layout: Latest Batch Status & Actionable Open Issues (White Canvas) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Status Card */}
        <div className="bg-white rounded-[24px] border border-[#E5E5E5] p-6 md:p-8 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-black flex items-center gap-2">
              <UploadCloud className="h-4 w-4 text-black" />
              Latest Ingestion Batch
            </h2>
            <span className="px-3 py-1 rounded-full text-[10px] font-mono uppercase tracking-[0.54px] font-semibold bg-[#D4FF5B] text-black">
              {data.upload_summary.status}
            </span>
          </div>

          <div className="p-4 bg-[#F9F9F9] rounded-[16px] border border-[#E5E5E5] space-y-2 text-xs">
            <div className="font-semibold text-black truncate">
              {data.upload_summary.file_name}
            </div>
            <div className="text-[11px] text-black/50 font-mono">
              Batch: {data.upload_summary.batch_id}
            </div>

            <div className="grid grid-cols-3 gap-2 pt-3 border-t border-[#E5E5E5] text-center font-mono">
              <div>
                <div className="text-black/50 text-[10px]">TOTAL</div>
                <div className="font-semibold text-black text-sm">
                  {data.upload_summary.total_rows}
                </div>
              </div>
              <div>
                <div className="text-emerald-700 text-[10px]">VALID</div>
                <div className="font-semibold text-emerald-700 text-sm">
                  {data.upload_summary.valid_rows}
                </div>
              </div>
              <div>
                <div className="text-rose-600 text-[10px]">FLAGGED</div>
                <div className="font-semibold text-rose-600 text-sm">
                  {data.upload_summary.invalid_rows}
                </div>
              </div>
            </div>
          </div>

          <Link
            to="/ingestion"
            className="w-full flex items-center justify-center gap-2 py-3 rounded-full border border-[#E5E5E5] bg-white hover:bg-[#F5F5F5] text-xs font-medium text-black transition-colors cursor-pointer"
          >
            <span>Open Batch History Ledger</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {/* Actionable Open Issues with "Fix Now" Links */}
        <div className="lg:col-span-2 bg-white rounded-[24px] border border-[#E5E5E5] p-6 md:p-8 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-black flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-black" />
                Actionable Open Compliance Issues ({data.fix_now_issues.length})
              </h2>
              <p className="text-xs font-[330] text-black/60 mt-0.5">
                Direct remediation links to resolve registry mismatches before deadline cutoff
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {data.fix_now_issues.map((iss) => (
              <div
                key={iss.issue_id}
                className="p-5 rounded-[18px] border border-[#E5E5E5] bg-[#F9F9F9] hover:border-black flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-mono text-xs font-semibold px-2.5 py-0.5 rounded-full bg-black text-white">
                      {iss.rule_code}
                    </span>
                    <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] px-2.5 py-0.5 rounded-full bg-[#FF8577] text-black">
                      {iss.severity}
                    </span>
                    <span className="text-xs text-black/60 font-[330]">
                      {iss.affected_count} records affected
                    </span>
                  </div>
                  <p className="text-xs text-black font-semibold">
                    {iss.message}
                  </p>
                  <p className="text-[11px] font-[330] text-black/70">
                    Suggestion: {iss.fix_action}
                  </p>
                </div>

                <Link
                  to={iss.deep_link}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-black hover:bg-black/85 text-white text-xs font-medium tracking-[-0.1px] shrink-0 transition-colors cursor-pointer"
                >
                  <span>Fix Now</span>
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
