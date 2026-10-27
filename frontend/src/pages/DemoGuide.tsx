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
    <div className="space-y-16 pb-16">
      {/* 1. LIME COLOR-BLOCK SECTION (Control Center & Sandbox Reset) */}
      <section className="rounded-[24px] p-8 md:p-12 bg-[#D4FF5B] text-black relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 relative z-10">
          <div className="space-y-4 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-semibold uppercase tracking-[0.54px] bg-black text-white">
              <span className="w-2 h-2 rounded-full bg-[#D4FF5B] animate-pulse" />
              DEMO MODE ACTIVE • 5-MINUTE LIVE EVALUATION
            </div>

            <h1 className="text-3xl md:text-5xl lg:text-6xl font-medium tracking-[-1.72px] text-black leading-[1.02]">
              Demonstration Control Center
            </h1>

            <p className="text-base md:text-xl font-[330] text-black/85 leading-[1.4] tracking-[-0.26px]">
              One-click role switching, instant database sandbox reset, prepared test files, and a timed 5-minute presentation script with exact spoken narration.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
            <button
              onClick={handleResetDemoData}
              disabled={isResetting}
              className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-full bg-black text-white text-[15px] font-medium tracking-[-0.1px] hover:bg-black/90 active:scale-[0.98] transition-all cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isResetting ? "animate-spin" : ""}`} />
              <span>{isResetting ? "Resetting Sandbox..." : "Reset Demo Data (< 3s)"}</span>
            </button>
            <button
              onClick={() => navigate("/")}
              className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-full bg-white text-black text-[15px] font-medium tracking-[-0.1px] hover:bg-white/90 border border-black/10 active:scale-[0.98] transition-all cursor-pointer"
            >
              <span>View AICTE Hub</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {resetMessage && (
          <div className="mt-6 p-4 rounded-[16px] bg-white/90 backdrop-blur border border-black/10 text-sm text-black font-medium">
            {resetMessage}
          </div>
        )}
      </section>

      {/* 2. WHITE CANVAS RETURN: MFA / TOTP Notice */}
      <section className="rounded-[20px] border border-[#E5E5E5] bg-[#F9F9F9] p-6 text-black flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <KeyRound className="w-5 h-5 text-black shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-mono text-xs font-semibold uppercase tracking-[0.54px] text-black/60">
              MFA / TOTP Sandbox Bypass
            </div>
            <p className="text-sm font-[330] text-black/80">
              When prompted for 6-digit TOTP verification on any account, enter{" "}
              <code className="font-mono font-semibold bg-white px-2 py-0.5 rounded-full border border-[#E5E5E5] text-black">
                000000
              </code>{" "}
              or{" "}
              <code className="font-mono font-semibold bg-white px-2 py-0.5 rounded-full border border-[#E5E5E5] text-black">
                123456
              </code>{" "}
              for instantaneous authentication without configuring Google Authenticator.
            </p>
          </div>
        </div>
      </section>

      {/* 3. NAVY COLOR-BLOCK SECTION (Pre-Configured Demo Accounts & Role Switcher) */}
      <section className="rounded-[24px] p-8 md:p-12 bg-[#0C1033] text-white space-y-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div className="space-y-2">
            <div className="font-mono text-xs font-semibold uppercase tracking-[0.54px] text-white/60">
              Identity & Scope Matrix
            </div>
            <h2 className="text-2xl md:text-4xl font-medium tracking-[-0.96px] text-white leading-tight">
              Pre-Configured Demo Personas
            </h2>
            <p className="text-sm md:text-base font-[330] text-white/70 max-w-xl">
              Click "One-Click Login" to generate an immediate JWT session and jump directly to that role's interface.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {accounts.map((acc) => {
            const Icon = acc.icon;
            return (
              <div
                key={acc.role}
                className="p-6 rounded-[20px] bg-white text-black flex flex-col justify-between space-y-6 shadow-sm hover:shadow-md transition-all"
              >
                <div className="space-y-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-[#F5F5F5] border border-[#E5E5E5] flex items-center justify-center text-black">
                        <Icon className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-[15px] font-semibold text-black tracking-[-0.2px]">
                          {acc.label}
                        </h3>
                        <span className="font-mono text-[11px] text-black/50 uppercase tracking-[0.54px]">
                          {acc.role}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="inline-block">
                    <span className="font-mono text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[#F5F5F5] text-black border border-[#E5E5E5]">
                      {acc.badge}
                    </span>
                  </div>

                  <p className="text-[13px] font-[330] text-black/75 leading-relaxed">
                    {acc.description}
                  </p>

                  <div className="space-y-2 pt-3 border-t border-[#E5E5E5] text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-black/50">Email:</span>
                      <div className="flex items-center gap-1.5 font-mono text-black font-medium">
                        <span>{acc.email}</span>
                        <button
                          onClick={() => handleCopy(acc.email, acc.email)}
                          className="hover:text-black text-black/40 cursor-pointer"
                          title="Copy email"
                        >
                          {copiedKey === acc.email ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-black/50">Password:</span>
                      <div className="flex items-center gap-1.5 font-mono text-black font-medium">
                        <span>{acc.pass}</span>
                        <button
                          onClick={() => handleCopy(acc.pass, acc.role + "_pass")}
                          className="hover:text-black text-black/40 cursor-pointer"
                          title="Copy password"
                        >
                          {copiedKey === acc.role + "_pass" ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
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
                  className="w-full inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full bg-black text-white text-xs font-medium tracking-[-0.1px] hover:bg-black/80 transition-all cursor-pointer"
                >
                  <span>One-Click Login</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* 4. CREAM COLOR-BLOCK SECTION (Prepared Demonstration Files) */}
      <section className="rounded-[24px] p-8 md:p-12 bg-[#FFF5EA] text-black space-y-8">
        <div className="space-y-2">
          <div className="font-mono text-xs font-semibold uppercase tracking-[0.54px] text-black/60">
            Ingestion Sandbox Assets
          </div>
          <h2 className="text-2xl md:text-4xl font-medium tracking-[-0.96px] text-black">
            Prepared Demonstration Files
          </h2>
          <p className="text-sm md:text-base font-[330] text-black/75 max-w-xl">
            Pre-crafted test datasets located in the project root ready for drag-and-drop live uploading into the ingestion portal.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-[20px] bg-white border border-[#E5E5E5] space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-black font-mono">clean.csv</span>
              <span className="font-mono text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-[#D2F8E7] text-black">
                100% Valid
              </span>
            </div>
            <p className="text-xs font-[330] text-black/75 leading-relaxed">
              60 student records within approved intake 60. Clean Verhoeff check digits, zero quota overflows, and perfect category quotas.
            </p>
            <div className="text-[11px] font-mono text-black/50 pt-2 border-t border-[#E5E5E5]">
              Path: /demo-assets/clean.csv
            </div>
          </div>

          <div className="p-6 rounded-[20px] bg-white border border-[#E5E5E5] space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-black font-mono">violation.csv</span>
              <span className="font-mono text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-[#FF8577] text-black">
                Live Anomaly Trigger
              </span>
            </div>
            <p className="text-xs font-[330] text-black/75 leading-relaxed">
              150 admissions uploaded against sanctioned intake 120 (30 overshoot) PLUS 2 cross-institution duplicates (already in DTU Delhi).
            </p>
            <div className="text-[11px] font-mono text-black/50 pt-2 border-t border-[#E5E5E5]">
              Path: /demo-assets/violation.csv
            </div>
          </div>

          <div className="p-6 rounded-[20px] bg-white border border-[#E5E5E5] space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-black font-mono">tamper_sample.json</span>
              <span className="font-mono text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-[#E5D4FF] text-black">
                Cryptographic Test
              </span>
            </div>
            <p className="text-xs font-[330] text-black/75 leading-relaxed">
              Valid Ed25519-signed academic credential. Modify CGPA from 8.92 to 9.92 to witness instant signature verification failure.
            </p>
            <div className="text-[11px] font-mono text-black/50 pt-2 border-t border-[#E5E5E5]">
              Path: /demo-assets/tamper_sample.json
            </div>
          </div>
        </div>
      </section>

      {/* 5. LILAC COLOR-BLOCK SECTION (5-Minute Choreographed Demonstration Script) */}
      <section className="rounded-[24px] p-8 md:p-12 bg-[#E5D4FF] text-black space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div className="space-y-2">
            <div className="font-mono text-xs font-semibold uppercase tracking-[0.54px] text-black/60">
              Choreographed Pitch
            </div>
            <h2 className="text-2xl md:text-4xl font-medium tracking-[-0.96px] text-black">
              5-Minute Demonstration Script
            </h2>
            <p className="text-sm md:text-base font-[330] text-black/75 max-w-xl">
              Follow this timed click path and word-for-word spoken narration during the Grand Finale evaluation.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="font-mono text-xs font-semibold px-3 py-1.5 rounded-full bg-white text-black border border-black/10">
              Completed: {Object.values(completedSteps).filter(Boolean).length} / {demoSteps.length} Steps
            </span>
            <button
              onClick={() => setCompletedSteps({})}
              className="px-4 py-1.5 rounded-full bg-[#FF2F7C] text-white text-xs font-medium tracking-[-0.1px] hover:bg-[#FF2F7C]/90 transition-all cursor-pointer"
            >
              Reset Steps
            </button>
          </div>
        </div>

        <div className="space-y-4">
          {demoSteps.map((step) => {
            const isCompleted = !!completedSteps[step.id];
            return (
              <div
                key={step.id}
                className={`p-6 rounded-[20px] transition-all bg-white border ${
                  isCompleted ? "border-emerald-500/40 bg-emerald-50/20" : "border-black/10 shadow-sm"
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <button
                      onClick={() => toggleStep(step.id)}
                      className={`mt-1 w-6 h-6 rounded-full flex items-center justify-center transition-colors cursor-pointer ${
                        isCompleted
                          ? "bg-black text-white"
                          : "border-2 border-black/20 hover:border-black text-transparent"
                      }`}
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs font-semibold px-2.5 py-0.5 rounded-full bg-black text-white">
                          {step.timestamp} ({step.duration})
                        </span>
                        <h3
                          className={`text-[15px] font-semibold ${
                            isCompleted ? "text-black/40 line-through" : "text-black"
                          }`}
                        >
                          Step {String.fromCharCode(65 + step.id)}: {step.title}
                        </h3>
                      </div>
                      <div className="text-xs text-black/70 font-medium flex items-center gap-1.5">
                        <PlayCircle className="w-3.5 h-3.5 text-black" />
                        <span>Action: {step.action}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => navigate(step.targetUrl)}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-medium bg-[#F5F5F5] hover:bg-black hover:text-white text-black transition-all shrink-0 cursor-pointer"
                  >
                    <span>Jump to Screen</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </div>

                {/* Spoken Narration Quote */}
                <div className="mt-4 ml-10 p-4 rounded-[16px] bg-[#F9F9F9] border border-[#E5E5E5] text-xs text-black/85 leading-relaxed italic">
                  <span className="font-semibold not-italic text-black font-mono uppercase text-[10px] tracking-[0.54px] block mb-1">
                    🎙️ Spoken Line:
                  </span>
                  "{step.narration}"
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
};

export default DemoGuide;
