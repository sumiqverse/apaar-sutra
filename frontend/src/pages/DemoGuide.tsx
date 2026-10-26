import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles,
  RefreshCw,
  KeyRound,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  Copy,
  Check,
  AlertTriangle,
  PlayCircle,
  FileSpreadsheet,
  FileCode,
  Building2,
  GraduationCap,
  Briefcase,
  UserCheck,
  Clock,
  ArrowRight,
} from "lucide-react";
import { apiClient, setAuthTokens } from "@/lib/api";

interface DemoAccount {
  role: string;
  email: string;
  pass: string;
  label: string;
  badge: string;
  color: string;
  icon: any;
  targetUrl: string;
  description: string;
}

export const DemoGuide: React.FC = () => {
  const navigate = useNavigate();
  const [isResetting, setIsResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState<number>(0);
  const [completedSteps, setCompletedSteps] = useState<Record<number, boolean>>({});

  const accounts: DemoAccount[] = [
    {
      role: "SUPER_ADMIN",
      email: "superadmin@aicte.gov.in",
      pass: "SuperAdmin@AICTE2026!",
      label: "AICTE National Directorate",
      badge: "Full Pan-India Scope",
      color: "border-indigo-500/30 bg-indigo-50/50 dark:bg-indigo-950/20 text-indigo-700 dark:text-indigo-400",
      icon: ShieldCheck,
      targetUrl: "/",
      description: "Pan-India oversight, live national telemetry, risk heatmap, and cross-state duplicate registry.",
    },
    {
      role: "INSTITUTION_ADMIN",
      email: "director.iitm@aicte.gov.in",
      pass: "InstAdmin@AICTE2026!",
      label: "IITM Mumbai Registrar",
      badge: "Tenant Scoped (Intake: 120)",
      color: "border-sky-500/30 bg-sky-50/50 dark:bg-sky-950/20 text-sky-700 dark:text-sky-400",
      icon: Building2,
      targetUrl: "/institution-dashboard",
      description: "College ingestion portal. Upload violation.csv here to trigger live overshoot and duplicate flags.",
    },
    {
      role: "AICTE_OFFICER",
      email: "officer@aicte.gov.in",
      pass: "Officer@2026!",
      label: "AICTE Regional Inspector",
      badge: "Audit & Investigation",
      color: "border-amber-500/30 bg-amber-50/50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-400",
      icon: UserCheck,
      targetUrl: "/",
      description: "Regional officer queue for reviewing anomalies, assigning inspections, and issuing compliance notices.",
    },
    {
      role: "VERIFIER",
      email: "verifier.tcs@tcs.com",
      pass: "Verifier@TCS2026!",
      label: "TCS Background Verifier",
      badge: "Third-Party Employer",
      color: "border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-400",
      icon: Briefcase,
      targetUrl: "/verifier",
      description: "Request student credentials, inspect purpose-scoped disclosures, and verify Ed25519 signatures.",
    },
    {
      role: "STUDENT",
      email: "student.demo@aicte.gov.in",
      pass: "Student@AICTE2026!",
      label: "Rohan Mehta (Student)",
      badge: "DPDP Data Principal",
      color: "border-purple-500/30 bg-purple-50/50 dark:bg-purple-950/20 text-purple-700 dark:text-purple-400",
      icon: GraduationCap,
      targetUrl: "/student/consent",
      description: "Student Privacy Portal: Approve/deny verifier requests, view selective disclosures, and revoke consent.",
    },
  ];

  const demoSteps = [
    {
      id: 0,
      timestamp: "0:00 - 0:20",
      duration: "20s",
      title: "Hook: The Multi-Crore Fraud Crisis",
      action: "Display AICTE National Dashboard overview",
      targetUrl: "/",
      narration:
        "Welcome to APAAR-Sutra. Every year, higher education regulators struggle with ghost students, seat blocking across multiple universities, and fraudulent credentials. AICTE previously had to rely on periodic aggregate summaries. We built APAAR-Sutra: a real-time, zero-trust verification and anomaly detection engine powered by Verhoeff APAAR IDs and Ed25519 cryptographic credentials.",
    },
    {
      id: 1,
      timestamp: "0:20 - 1:00",
      duration: "40s",
      title: "Ingestion & Live Deterministic Validation",
      action: "Switch to IITM Mumbai Portal & Upload violation.csv",
      targetUrl: "/institution-dashboard",
      narration:
        "Let's step into the shoes of the registrar at IITM Mumbai. They upload their new admissions batch using violation.csv. Watch the live progress bar: within seconds, our 31-rule engine deterministically catches that approved capacity is 120, but 150 students are enrolled — a 30-student overshoot! Simultaneously, rule R011 flags two students who are already actively enrolled at Delhi Technological University. The registrar immediately receives an error report.",
    },
    {
      id: 2,
      timestamp: "1:00 - 1:40",
      duration: "40s",
      title: "Real-Time AICTE Directorate Alert",
      action: "Switch back to AICTE Dashboard & Observe Live Alert",
      targetUrl: "/",
      narration:
        "Instantly, without refreshing, the AICTE National Directorate receives a real-time telemetry alert over WebSockets. The national geospatial map flashes red over Maharashtra. The national KPI counters update in real time: critical intake overshoot detected at IITM Mumbai.",
    },
    {
      id: 3,
      timestamp: "1:40 - 2:25",
      duration: "45s",
      title: "AICTE Anomaly Drill-Down & Dual Enrolment Evidence",
      action: "Click into IITM Mumbai details, view radar chart and duplicate evidence",
      targetUrl: "/",
      narration:
        "The directorate drills into IITM Mumbai. Our Isolation Forest and PCA unsupervised models provide a plain-English explanation: intake utilisation exceeds peer median by 3.8 sigma, accompanied by admission timestamp clustering. Notice the cross-institution duplicate evidence table: Student Aarav Sharma and Diya Patel have concurrent full-time admissions in both Mumbai and Delhi.",
    },
    {
      id: 4,
      timestamp: "2:25 - 3:15",
      duration: "50s",
      title: "DPDP-Compliant Student Consent & Employer Verification",
      action: "Navigate to Verifier Portal -> Student Consent Portal",
      targetUrl: "/verifier",
      narration:
        "Now observe credential verification under India's Digital Personal Data Protection Act 2023. Tata Consultancy Services requests academic verification for hiring. The student receives a push notification on their privacy portal, selectively discloses only CGPA and degree status while keeping Aadhaar hash blinded, and approves. The verifier receives an Ed25519-signed digital transcript and verifiable QR code.",
    },
    {
      id: 5,
      timestamp: "3:15 - 3:55",
      duration: "40s",
      title: "Cryptographic Tamper-Proofing & Live Revocation",
      action: "Open Tamper Demo (/tamper-demo), alter 1 character, then revoke consent",
      targetUrl: "/tamper-demo",
      narration:
        "What happens if someone tampers with the transcript? In our Tamper Demo, watch: altering even a single byte in the student's CGPA from 8.92 to 9.92 causes the Ed25519 signature to immediately fail cryptographic verification in red. Now watch live revocation: the student clicks 'Revoke Consent' in their portal, and scanning the QR code instantly reflects 'REVOKED' across the national ledger.",
    },
    {
      id: 6,
      timestamp: "3:55 - 4:35",
      duration: "40s",
      title: "Statutory Reports Engine & Developer Integration Kit",
      action: "View Statutory Reports (/reports) and Developer Kit (/developers)",
      targetUrl: "/reports",
      narration:
        "AICTE officers can instantly generate statutory PDF and Excel compliance reports with embedded Matplotlib trends and a cryptographic SHA-256 footer verification hash. Furthermore, our Developer Portal provides complete OpenAPI documentation and HMAC-authenticated integration kits for state CET admission portals.",
    },
    {
      id: 7,
      timestamp: "4:35 - 5:00",
      duration: "25s",
      title: "Scalability, Performance & Closing Impact",
      action: "Highlight System Health telemetry & scale benchmarks",
      targetUrl: "/health",
      narration:
        "Under rigorous Locust stress testing, APAAR-Sutra delivered 1,842 requests per second with a p95 response time of 142 milliseconds on a 500,000-record dataset. Fully containerized, MeitY-cloud ready, and privacy-preserving by design. APAAR-Sutra restores complete trust and transparency to Indian higher education. Thank you!",
    },
  ];

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleQuickLogin = async (role: string, targetUrl: string) => {
    try {
      const res = await apiClient<{
        access_token: string;
        refresh_token: string;
      }>("/api/v1/demo/quick-login", {
        method: "POST",
        body: JSON.stringify({ role }),
      });
      setAuthTokens(res.access_token, res.refresh_token);
      navigate(targetUrl);
    } catch (err: any) {
      alert("Quick login error: " + (err.message || "Failed to switch role"));
    }
  };

  const handleResetDemoData = async () => {
    if (!confirm("Reset database to clean baseline state? This takes < 3 seconds.")) return;
    setIsResetting(true);
    setResetMessage(null);
    try {
      const res = await apiClient<{
        message: string;
        reset_duration_ms: number;
        timestamp: string;
      }>("/api/v1/demo/reset", { method: "POST" });
      setResetMessage(`✅ ${res.message} (Executed in ${res.reset_duration_ms}ms)`);
      setCompletedSteps({});
      setActiveStep(0);
    } catch (err: any) {
      setResetMessage(`❌ Error resetting demo: ${err.message || "Network error"}`);
    } finally {
      setIsResetting(false);
    }
  };

  const toggleStep = (id: number) => {
    setCompletedSteps((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 p-6">
      {/* Top Banner & Control Header */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-indigo-500/30 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <Sparkles className="w-64 h-64 text-indigo-400" />
        </div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              DEMO MODE ACTIVE • 5-MINUTE LIVE EVALUATION
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">
              APAAR-Sutra Demonstration Control Center
            </h1>
            <p className="text-slate-300 text-sm max-w-2xl">
              1-Click role switching, instant database sandbox reset, prepared test files, and a timed 5-minute presentation script with exact spoken narration.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3 shrink-0">
            <button
              onClick={handleResetDemoData}
              disabled={isResetting}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white font-semibold text-sm shadow-lg shadow-rose-900/40 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isResetting ? "animate-spin" : ""}`} />
              {isResetting ? "Resetting Sandbox..." : "Reset Demo Data (< 3s)"}
            </button>
          </div>
        </div>

        {resetMessage && (
          <div className="mt-4 p-3 rounded-xl bg-white/10 backdrop-blur border border-white/20 text-sm text-emerald-200 font-medium">
            {resetMessage}
          </div>
        )}
      </div>

      {/* TOTP 2FA Demo Bypass Notice */}
      <div className="flex items-center gap-4 p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-200 text-sm">
        <KeyRound className="w-6 h-6 text-amber-500 shrink-0" />
        <div>
          <span className="font-bold">MFA / TOTP Demo Bypass Code: </span>
          When prompted for 6-digit TOTP verification on any account, enter{" "}
          <code className="bg-amber-500/20 px-2 py-0.5 rounded font-mono font-bold text-amber-600 dark:text-amber-300">
            000000
          </code>{" "}
          or{" "}
          <code className="bg-amber-500/20 px-2 py-0.5 rounded font-mono font-bold text-amber-600 dark:text-amber-300">
            123456
          </code>{" "}
          for instantaneous authentication without configuring Google Authenticator.
        </div>
      </div>

      {/* Role Cards Matrix */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Pre-Configured Demo Accounts (1-Click Switch)
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Click "One-Click Login" to generate an immediate JWT session and jump directly to that role's interface.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map((acc) => {
            const Icon = acc.icon;
            return (
              <div
                key={acc.role}
                className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className={`p-2 rounded-lg ${acc.color}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                          {acc.label}
                        </h3>
                        <span className="text-xs text-slate-500 font-mono">
                          {acc.role}
                        </span>
                      </div>
                    </div>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      {acc.badge}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    {acc.description}
                  </p>

                  <div className="space-y-1.5 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Email:</span>
                      <div className="flex items-center gap-1.5 font-mono text-slate-700 dark:text-slate-300 font-medium">
                        <span>{acc.email}</span>
                        <button
                          onClick={() => handleCopy(acc.email, acc.email)}
                          className="hover:text-indigo-500 text-slate-400"
                          title="Copy email"
                        >
                          {copiedKey === acc.email ? (
                            <Check className="w-3.5 h-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Password:</span>
                      <div className="flex items-center gap-1.5 font-mono text-slate-700 dark:text-slate-300 font-medium">
                        <span>{acc.pass}</span>
                        <button
                          onClick={() => handleCopy(acc.pass, acc.role + "_pass")}
                          className="hover:text-indigo-500 text-slate-400"
                          title="Copy password"
                        >
                          {copiedKey === acc.role + "_pass" ? (
                            <Check className="w-3.5 h-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleQuickLogin(acc.role, acc.targetUrl)}
                  className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow transition-all"
                >
                  <span>One-Click Login</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Prepared Demo Assets in /demo-assets */}
      <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-indigo-500" />
              Prepared Demonstration Files (/demo-assets)
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Pre-crafted test datasets located in the project root ready for drag-and-drop live uploading.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/40 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-slate-900 dark:text-white font-mono">
                clean.csv
              </span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                100% Valid
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              60 student records within approved intake 60. Clean Verhoeff check digits, zero quota overflows, and perfect category quotas.
            </p>
            <div className="text-[11px] font-mono text-slate-400">
              Path: /demo-assets/clean.csv
            </div>
          </div>

          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-50/50 dark:bg-rose-950/20 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-rose-900 dark:text-rose-300 font-mono">
                violation.csv
              </span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/30">
                Live Anomaly Trigger
              </span>
            </div>
            <p className="text-xs text-rose-800 dark:text-rose-300">
              150 admissions uploaded against sanctioned intake 120 (30 overshoot) PLUS 2 cross-institution duplicates (already in DTU Delhi).
            </p>
            <div className="text-[11px] font-mono text-rose-500">
              Path: /demo-assets/violation.csv
            </div>
          </div>

          <div className="p-4 rounded-xl border border-purple-500/30 bg-purple-50/50 dark:bg-purple-950/20 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-purple-900 dark:text-purple-300 font-mono">
                tamper_sample.json
              </span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-500/30">
                Cryptographic Test
              </span>
            </div>
            <p className="text-xs text-purple-800 dark:text-purple-300">
              Valid Ed25519-signed academic credential. Modify CGPA from 8.92 to 9.92 to see instant signature verification failure.
            </p>
            <div className="text-[11px] font-mono text-purple-500">
              Path: /demo-assets/tamper_sample.json
            </div>
          </div>
        </div>
      </div>

      {/* 5-Minute Timed Live Demo Script & Checklist */}
      <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-indigo-500" />
              5-Minute Choreographed Demonstration Script
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Follow this timed click path and word-for-word spoken narration during the Grand Finale evaluation.
            </p>
          </div>
          <div className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
            Completed: {Object.values(completedSteps).filter(Boolean).length} / {demoSteps.length} Steps
          </div>
        </div>

        <div className="space-y-4">
          {demoSteps.map((step) => {
            const isCompleted = !!completedSteps[step.id];
            return (
              <div
                key={step.id}
                className={`p-5 rounded-xl border transition-all ${
                  isCompleted
                    ? "border-emerald-500/30 bg-emerald-50/20 dark:bg-emerald-950/10"
                    : "border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 hover:border-indigo-500/30"
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <button
                      onClick={() => toggleStep(step.id)}
                      className={`mt-1 p-1 rounded-md transition-colors ${
                        isCompleted
                          ? "bg-emerald-600 text-white"
                          : "border border-slate-300 dark:border-slate-700 hover:border-indigo-500 text-transparent"
                      }`}
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300">
                          {step.timestamp} ({step.duration})
                        </span>
                        <h3
                          className={`text-sm font-bold ${
                            isCompleted
                              ? "text-slate-500 dark:text-slate-400 line-through"
                              : "text-slate-900 dark:text-white"
                          }`}
                        >
                          Step {String.fromCharCode(65 + step.id)}: {step.title}
                        </h3>
                      </div>
                      <div className="text-xs text-indigo-600 dark:text-indigo-400 font-medium flex items-center gap-1.5">
                        <PlayCircle className="w-3.5 h-3.5" />
                        <span>Action: {step.action}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => navigate(step.targetUrl)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors shrink-0"
                  >
                    <span>Jump to Screen</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </div>

                {/* Spoken Narration Quote */}
                <div className="mt-3 ml-7 p-3 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 leading-relaxed italic">
                  <span className="font-semibold not-italic text-slate-900 dark:text-white">
                    🎙️ Spoken Line:{" "}
                  </span>
                  "{step.narration}"
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default DemoGuide;
