import React, { useEffect, useState } from "react";
import {
  X,
  Building2,
  AlertTriangle,
  Clock,
  BrainCircuit,
  Hash,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { api } from "@/lib/api";

interface ProgramCapacity {
  id: string;
  name: string;
  branch: string;
  level: string;
  approved_intake: number;
  regular_enrolment: number;
  supernumerary_enrolment: number;
  total_enrolment: number;
  utilisation_pct: number;
  has_overshoot: boolean;
  supernumerary_pct: number;
}

interface ValidationIssue {
  id: string;
  rule_code: string;
  severity: string;
  message: string;
  explanation: Record<string, any>;
  status: string;
  created_at: string;
}

interface TimelineEvent {
  id: string;
  event_type: string;
  title: string;
  description: string;
  timestamp: string;
  badge?: string;
}

interface AuditActivity {
  id: string;
  seq: number;
  actor_id: string;
  actor_role: string;
  action: string;
  entity_type: string;
  timestamp: string;
}

interface InstitutionDrilldownData {
  id: string;
  aicte_id: string;
  name: string;
  state_name: string;
  state_code: string;
  district?: string;
  institution_type: string;
  email?: string;
  status: string;
  approved_total_intake: number;
  current_total_enrolment: number;
  intake_utilisation_pct: number;
  risk_score: number;
  risk_level: string;
  anomaly_score: number;
  contributing_factors: any[];
  peer_comparison: Record<string, any>;
  ghost_student_flags: Record<string, any>;
  programs: ProgramCapacity[];
  open_issues: ValidationIssue[];
  timeline: TimelineEvent[];
  recent_audit: AuditActivity[];
}

interface InstitutionDrilldownModalProps {
  institutionId: string | null;
  onClose: () => void;
}

export const InstitutionDrilldownModal: React.FC<InstitutionDrilldownModalProps> = ({
  institutionId,
  onClose,
}) => {
  const [data, setData] = useState<InstitutionDrilldownData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"programs" | "anomalies" | "issues" | "timeline" | "audit">("programs");

  useEffect(() => {
    if (!institutionId) {
      setData(null);
      return;
    }

    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.get<InstitutionDrilldownData>(
          `/api/v1/analytics/institution-drilldown/${institutionId}`
        );
        setData(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to load institution details");
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [institutionId]);

  if (!institutionId) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Top Header */}
        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-start justify-between bg-slate-50/50 dark:bg-slate-800/40">
          <div>
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-brand-100 dark:bg-brand-950 text-brand-700 dark:text-brand-300 font-semibold">
                {data?.aicte_id || "Loading..."}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium">
                {data?.institution_type}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium">
                {data?.state_name} ({data?.state_code})
              </span>
              {data && (
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${
                    data.risk_score >= 80
                      ? "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-400"
                      : data.risk_score >= 50
                      ? "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-400"
                      : "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-400"
                  }`}
                >
                  Risk Score: {data.risk_score.toFixed(1)} / 100 ({data.risk_level})
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">
              {data?.name || "Institution Drilldown"}
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {data?.district ? `${data.district}, ` : ""}
              {data?.state_name} • Contact: {data?.email || "aicte-admin@portal.gov.in"}
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-200 dark:border-slate-800 px-6 gap-6 bg-white dark:bg-slate-900 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab("programs")}
            className={`py-3 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "programs"
                ? "border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <Building2 className="h-4 w-4" />
            Programs & Capacity Bars ({data?.programs.length || 0})
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("anomalies")}
            className={`py-3 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "anomalies"
                ? "border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <BrainCircuit className="h-4 w-4" />
            Anomaly Explanations ({data?.contributing_factors.length || 0})
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("issues")}
            className={`py-3 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "issues"
                ? "border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <AlertTriangle className="h-4 w-4" />
            Validation Issues ({data?.open_issues.length || 0})
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("timeline")}
            className={`py-3 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "timeline"
                ? "border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <Clock className="h-4 w-4" />
            Timeline ({data?.timeline.length || 0})
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("audit")}
            className={`py-3 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "audit"
                ? "border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <Hash className="h-4 w-4" />
            Audit Trail
          </button>
        </div>

        {/* Modal Body Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600"></div>
              <p className="text-xs text-slate-500">Loading deep institutional telemetry...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-rose-50 text-rose-700 rounded-lg text-sm">{error}</div>
          ) : data ? (
            <>
              {/* TAB 1: Programs & Capacity Bars */}
              {activeTab === "programs" && (
                <div className="space-y-6">
                  {/* Capacity Bar Chart */}
                  <div className="bg-slate-50 dark:bg-slate-800/40 p-5 rounded-xl border border-slate-200 dark:border-slate-700/60">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
                      Program-wise Approved Intake vs. Actual Regular & Supernumerary Enrolments
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
                      Direct comparison across approved branch quotas (overshoot flagged automatically)
                    </p>

                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={data.programs.map((p) => ({
                            name: p.branch || p.name,
                            approved: p.approved_intake,
                            regular: p.regular_enrolment,
                            supernumerary: p.supernumerary_enrolment,
                          }))}
                          margin={{ top: 10, right: 10, left: 0, bottom: 20 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#cbd5e1" />
                          <XAxis dataKey="name" stroke="#64748b" fontSize={11} interval={0} angle={-15} textAnchor="end" />
                          <YAxis stroke="#64748b" fontSize={11} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "#0f172a",
                              borderColor: "#334155",
                              color: "#fff",
                              borderRadius: "8px",
                              fontSize: "12px",
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                          <Bar dataKey="approved" name="Approved Intake" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                          <Bar dataKey="regular" name="Regular Enrolled" fill="#0284c7" radius={[4, 4, 0, 0]} />
                          <Bar dataKey="supernumerary" name="Supernumerary Seats" fill="#ea580c" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Program Detail Table */}
                  <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-700">
                        <tr>
                          <th className="py-2.5 px-3">Program / Branch</th>
                          <th className="py-2.5 px-3">Level</th>
                          <th className="py-2.5 px-3 text-right">Approved</th>
                          <th className="py-2.5 px-3 text-right">Regular</th>
                          <th className="py-2.5 px-3 text-right">Supernumerary</th>
                          <th className="py-2.5 px-3 text-center">Utilisation</th>
                          <th className="py-2.5 px-3 text-center">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {data.programs.map((p) => (
                          <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                            <td className="py-2.5 px-3 font-medium text-slate-900 dark:text-white">
                              {p.name} ({p.branch})
                            </td>
                            <td className="py-2.5 px-3">{p.level}</td>
                            <td className="py-2.5 px-3 text-right font-mono">{p.approved_intake}</td>
                            <td className="py-2.5 px-3 text-right font-mono">{p.regular_enrolment}</td>
                            <td className="py-2.5 px-3 text-right font-mono text-amber-600 dark:text-amber-400">
                              {p.supernumerary_enrolment} ({p.supernumerary_pct}%)
                            </td>
                            <td className="py-2.5 px-3 text-center font-mono font-semibold">
                              {p.utilisation_pct}%
                            </td>
                            <td className="py-2.5 px-3 text-center">
                              {p.has_overshoot ? (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-400">
                                  CAP OVERRUN
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
                                  COMPLIANT
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* TAB 2: Anomaly Explanations */}
              {activeTab === "anomalies" && (
                <div className="space-y-4">
                  <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
                      Isolation Forest & Statistical Z-Score Explanations
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Explainable AI output: contributing factors identified by institutional feature deviation analysis
                    </p>
                  </div>

                  {data.contributing_factors.length === 0 ? (
                    <div className="p-8 text-center text-slate-400 bg-slate-50 dark:bg-slate-800/20 rounded-xl">
                      No significant statistical anomaly deviations detected for this institution.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {data.contributing_factors.map((factor, idx) => (
                        <div
                          key={idx}
                          className="p-4 rounded-xl border border-amber-200 dark:border-amber-900/40 bg-amber-50/50 dark:bg-amber-950/20 flex items-start gap-3"
                        >
                          <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                              {factor.feature?.replace(/_/g, " ")}
                            </h4>
                            <p className="text-xs text-slate-700 dark:text-slate-300 mt-1 font-medium">
                              {factor.plain_english || factor.description}
                            </p>
                            {factor.deviation_pct && (
                              <div className="mt-2 text-[11px] text-amber-800 dark:text-amber-300">
                                Deviation: +{factor.deviation_pct.toFixed(1)}% vs Peer Median • Z-Score:{" "}
                                {factor.z_score?.toFixed(2) || "N/A"}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: Validation Issues */}
              {activeTab === "issues" && (
                <div className="space-y-3">
                  {data.open_issues.length === 0 ? (
                    <div className="p-8 text-center text-slate-400 bg-slate-50 dark:bg-slate-800/20 rounded-xl">
                      No open validation rule violations flagged.
                    </div>
                  ) : (
                    data.open_issues.map((iss) => (
                      <div
                        key={iss.id}
                        className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/40 flex items-start justify-between gap-4"
                      >
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-200">
                              {iss.rule_code}
                            </span>
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                                iss.severity === "CRITICAL" || iss.severity === "ERROR"
                                  ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                                  : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                              }`}
                            >
                              {iss.severity}
                            </span>
                            <span className="text-[11px] text-slate-400 font-mono">
                              {new Date(iss.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <p className="text-xs text-slate-800 dark:text-slate-200 font-medium">
                            {iss.message}
                          </p>
                        </div>

                        <span className="text-xs font-semibold px-2 py-1 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                          {iss.status}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* TAB 4: Timeline */}
              {activeTab === "timeline" && (
                <div className="space-y-4">
                  <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 dark:before:bg-slate-700">
                    {data.timeline.map((event) => (
                      <div key={event.id} className="relative">
                        <span className="absolute -left-6 top-1 h-3.5 w-3.5 rounded-full bg-brand-500 border-2 border-white dark:border-slate-900" />
                        <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700">
                          <div className="flex items-center justify-between mb-1">
                            <h4 className="text-xs font-bold text-slate-900 dark:text-white">
                              {event.title}
                            </h4>
                            <span className="text-[10px] text-slate-400 font-mono">
                              {new Date(event.timestamp).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-xs text-slate-600 dark:text-slate-300">
                            {event.description}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 5: Audit Trail */}
              {activeTab === "audit" && (
                <div className="space-y-3">
                  <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg text-xs text-slate-500 border border-slate-200 dark:border-slate-700">
                    SHA-256 hash-chained sequence entries recorded in immutable ledger
                  </div>
                  <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        <tr>
                          <th className="py-2 px-3">Seq</th>
                          <th className="py-2 px-3">Action</th>
                          <th className="py-2 px-3">Actor Role</th>
                          <th className="py-2 px-3">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {data.recent_audit.map((a) => (
                          <tr key={a.id}>
                            <td className="py-2 px-3 font-bold text-slate-500">#{a.seq}</td>
                            <td className="py-2 px-3 text-brand-600 dark:text-brand-400 font-semibold">{a.action}</td>
                            <td className="py-2 px-3 text-slate-600 dark:text-slate-300">{a.actor_role}</td>
                            <td className="py-2 px-3 text-slate-400">{new Date(a.timestamp).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};
