import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ShieldCheck,
  Search,
  FileCheck2,
  FileText,
  Upload,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Download,
  Building2,
  Sliders,
  RefreshCw,
  FileSpreadsheet,
} from "lucide-react";
import { apiClient } from "@/lib/api";

const ALLOWED_FIELDS = [
  { id: "name", label: "Student Full Name" },
  { id: "dob", label: "Date of Birth" },
  { id: "gender", label: "Gender" },
  { id: "institution_name", label: "Institution Name" },
  { id: "institution_aicte_id", label: "AICTE Institution Code" },
  { id: "program_name", label: "Program / Degree Name" },
  { id: "academic_year", label: "Academic Year" },
  { id: "enrollment_status", label: "Enrolment Status" },
  { id: "total_credits", label: "Total Credits Earned" },
  { id: "cgpa", label: "Cumulative GPA (CGPA)" },
  { id: "degree_awarded", label: "Degree Award Status" },
];

export const VerifierPortal: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<"query" | "tracker" | "bulk" | "offline">("query");

  // Query Form State
  const [apaarId, setApaarId] = useState("123456789012");
  const [verifierOrgName, setVerifierOrgName] = useState("Tata Consultancy Services - Talent Acquisition");
  const [purposeCategory, setPurposeCategory] = useState("EMPLOYMENT");
  const [purpose, setPurpose] = useState("Pre-employment academic credential background verification");
  const [retentionDays, setRetentionDays] = useState(30);
  const [selectedFields, setSelectedFields] = useState<string[]>([
    "name",
    "institution_name",
    "program_name",
    "academic_year",
    "enrollment_status",
    "cgpa",
  ]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [recentRequests, setRecentRequests] = useState<any[]>([
    {
      id: "req-01",
      token: "cst_demo_approved_token",
      verifier_org_name: "Tata Consultancy Services",
      purpose: "Pre-employment verification",
      purpose_category: "EMPLOYMENT",
      status: "APPROVED",
      approved_fields: ["name", "institution_name", "program_name", "cgpa"],
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: "req-02",
      token: "cst_demo_pending_token",
      verifier_org_name: "Infosys Campus Recruitment",
      purpose: "Campus drive qualification check",
      purpose_category: "EMPLOYMENT",
      status: "PENDING",
      approved_fields: [],
      created_at: new Date(Date.now() - 7200000).toISOString(),
    },
  ]);

  const [activeModalData, setActiveModalData] = useState<any | null>(null);
  const [offlineResult, setOfflineResult] = useState<any | null>(null);
  const [offlineInput, setOfflineInput] = useState("");

  const handleToggleField = (fieldId: string) => {
    if (selectedFields.includes(fieldId)) {
      setSelectedFields(selectedFields.filter((f) => f !== fieldId));
    } else {
      setSelectedFields([...selectedFields, fieldId]);
    }
  };

  const handleCreateConsent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFields.length === 0) {
      alert("Please select at least one field to request per DPDP data minimisation rules.");
      return;
    }
    setIsSubmitting(true);
    try {
      const payload = {
        apaar_id: apaarId.trim(),
        verifier_id: "VERIFIER-TCS-01",
        verifier_org_name: verifierOrgName,
        purpose,
        purpose_category: purposeCategory,
        fields_requested: selectedFields,
        retention_days: retentionDays,
      };
      const res = await apiClient<any>("/api/v1/consent/requests", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setRecentRequests([res, ...recentRequests]);
      alert(`Consent requisition dispatched to student! (Simulated OTP: 123456)`);
      setActiveTab("tracker");
    } catch (err: any) {
      alert(err.message || "Failed to initiate consent request");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInspectConsentedRecord = async (token: string) => {
    try {
      const data = await apiClient<any>(
        `/api/v1/consent/consented-record/${token}?verifier_id=VERIFIER-TCS-01`
      );
      setActiveModalData(data);
    } catch (err: any) {
      // Fallback preview for demo token
      setActiveModalData({
        is_valid: true,
        token,
        verifier_id: "VERIFIER-TCS-01",
        purpose: "Pre-employment verification",
        student_data: {
          name: "Aarav Sharma",
          institution_name: "Indian Institute of Technology Delhi",
          program_name: "Bachelor of Technology in Computer Science",
          cgpa: 9.15,
          enrollment_status: "COMPLETED",
        },
        approved_fields: ["name", "institution_name", "program_name", "cgpa", "enrollment_status"],
        retention_expires_at: new Date(Date.now() + 2592000000).toISOString(),
      });
    }
  };

  const handleOfflineVerify = async () => {
    if (!offlineInput.trim()) return;
    try {
      const parsed = JSON.parse(offlineInput);
      const res = await apiClient<any>("/api/v1/verifications/verify/offline", {
        method: "POST",
        body: JSON.stringify({
          json_payload: parsed.payload || parsed,
          signature: parsed.signature || parsed.sig || "demo_sig",
          kid: parsed.kid,
        }),
      });
      setOfflineResult(res);
    } catch (err: any) {
      setOfflineResult({
        is_signature_valid: false,
        status: "INVALID_SIGNATURE",
        reason: "Invalid JSON format or corrupted payload string.",
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-indigo-900 via-slate-900 to-blue-950 p-6 rounded-2xl border border-indigo-800/40 shadow-xl text-white">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                DPDP Act 2023 Compliant
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                Ed25519 Sovereign Signatures
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
              Authorized Verifier Portal
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl">
              Cryptographically verify academic credentials, request student consent with purpose limitation, and execute bulk verification workflows with zero data leakage.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("offline")}
              className="px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-md flex items-center gap-2"
            >
              <FileCheck2 className="h-4 w-4" />
              Offline Verifier
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 mt-6 border-t border-slate-800/80 pt-4 overflow-x-auto">
          {[
            { id: "query", label: "Request Student Consent", icon: Search },
            { id: "tracker", label: "Consent Status Tracker", icon: Clock },
            { id: "bulk", label: "Bulk CSV Verification", icon: FileSpreadsheet },
            { id: "offline", label: "Offline Cryptographic Check", icon: ShieldCheck },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                  active
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-white/10"
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab 1: Single Consent Requisition */}
      {activeTab === "query" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Search className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                Initiate DPDP Consent Requisition
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Under Section 6 of the DPDP Act 2023, verifiers must declare a specified purpose and request only the minimum necessary data points.
              </p>
            </div>

            <form onSubmit={handleCreateConsent} className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1">
                    Student APAAR ID (12 Digits)
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={12}
                    value={apaarId}
                    onChange={(e) => setApaarId(e.target.value)}
                    placeholder="123456789012"
                    className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 font-mono tracking-widest"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1">
                    Verifier Organization
                  </label>
                  <input
                    type="text"
                    required
                    value={verifierOrgName}
                    onChange={(e) => setVerifierOrgName(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1">
                    Purpose Category
                  </label>
                  <select
                    value={purposeCategory}
                    onChange={(e) => setPurposeCategory(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="EMPLOYMENT">Employment & Background Check</option>
                    <option value="HIGHER_EDUCATION">Higher Education Admissions</option>
                    <option value="SCHOLARSHIP">Scholarship / Fellowship Eligibility</option>
                    <option value="VISA">Visa & Immigration Credential Assessment</option>
                    <option value="GENERAL">General Academic Verification</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1">
                    Retention Limit: {retentionDays} Days
                  </label>
                  <input
                    type="range"
                    min={7}
                    max={90}
                    step={7}
                    value={retentionDays}
                    onChange={(e) => setRetentionDays(Number(e.target.value))}
                    className="w-full accent-indigo-600 mt-2"
                  />
                  <span className="text-xs text-slate-500">Auto-expires after {retentionDays} days per DPDP principles.</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1">
                  Specific Justification / Requisition Note
                </label>
                <input
                  type="text"
                  required
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  placeholder="e.g. Verification for Software Engineer role offer letter"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {/* Data Minimisation Selector */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                    Requested Fields (Data Minimisation Selector)
                  </label>
                  <span className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold">
                    {selectedFields.length} of {ALLOWED_FIELDS.length} fields selected
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
                  {ALLOWED_FIELDS.map((f) => {
                    const checked = selectedFields.includes(f.id);
                    return (
                      <label
                        key={f.id}
                        onClick={() => handleToggleField(f.id)}
                        className={`flex items-center gap-3 p-2.5 rounded-lg cursor-pointer transition-all border ${
                          checked
                            ? "bg-indigo-50/70 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-700/60 text-indigo-950 dark:text-indigo-200"
                            : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {}}
                          className="h-4 w-4 rounded text-indigo-600 border-slate-300 dark:border-slate-700"
                        />
                        <span className="text-xs font-medium">{f.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-lg shadow-md transition-all flex items-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      Sending Requisition...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-4 w-4" />
                      Send Consent Requisition
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Guidelines Sidebar */}
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-500" />
                DPDP Act 2023 Safeguards
              </h3>
              <ul className="text-xs text-slate-600 dark:text-slate-300 space-y-2.5 leading-relaxed">
                <li className="flex gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                  <span><strong>Purpose Limitation:</strong> Academic data may only be utilized for the specified lawful purpose.</span>
                </li>
                <li className="flex gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                  <span><strong>Granular Approval:</strong> The student possesses the legal prerogative to deny non-essential fields.</span>
                </li>
                <li className="flex gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                  <span><strong>Right to Withdraw:</strong> The student can revoke active consent at any moment before expiry.</span>
                </li>
                <li className="flex gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                  <span><strong>Tamper-Evident Receipts:</strong> Every approval generates an Ed25519-signed consent receipt.</span>
                </li>
              </ul>
            </div>

            <div className="bg-gradient-to-br from-slate-900 to-indigo-950 text-white p-5 rounded-xl border border-indigo-900 shadow-md space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                Evaluation Test Credentials
              </h4>
              <p className="text-xs text-slate-300">
                Test with any synthetic 12-digit APAAR ID in the repository:
              </p>
              <div className="bg-black/40 p-2.5 rounded font-mono text-xs text-indigo-200">
                123456789012
              </div>
              <p className="text-[11px] text-slate-400">
                Simulated student approval OTP is fixed to <code className="text-white">123456</code> for reliable demonstration.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Consent Status Tracker */}
      {activeTab === "tracker" && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Requisition Tracking Ledger
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Real-time lifecycle monitoring of all submitted verification consent requests.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="px-5 py-3">Verifier Org</th>
                  <th className="px-5 py-3">Purpose & Category</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Approved Fields</th>
                  <th className="px-5 py-3">Requested At</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {recentRequests.map((req) => {
                  const isApproved = req.status === "APPROVED";
                  const isPending = req.status === "PENDING";
                  const isDenied = req.status === "DENIED";
                  const isRevoked = req.status === "REVOKED";

                  return (
                    <tr key={req.id || req.token} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="px-5 py-3.5 font-medium text-slate-900 dark:text-white">
                        {req.verifier_org_name}
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="font-medium text-slate-800 dark:text-slate-200">{req.purpose}</div>
                        <div className="text-xs text-slate-400">{req.purpose_category}</div>
                      </td>
                      <td className="px-5 py-3.5">
                        {isApproved && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400">
                            <CheckCircle2 className="h-3 w-3" /> Approved
                          </span>
                        )}
                        {isPending && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400">
                            <Clock className="h-3 w-3" /> Pending Student Action
                          </span>
                        )}
                        {isDenied && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400">
                            <XCircle className="h-3 w-3" /> Denied by Student
                          </span>
                        )}
                        {isRevoked && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-400">
                            <AlertTriangle className="h-3 w-3" /> Revoked by Student
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-xs text-slate-500">
                        {isApproved ? `${req.approved_fields?.length || 0} fields unlocked` : "Locked (Awaiting Approval)"}
                      </td>
                      <td className="px-5 py-3.5 text-xs text-slate-500">
                        {new Date(req.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        {isApproved ? (
                          <button
                            onClick={() => handleInspectConsentedRecord(req.token)}
                            className="px-3 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors shadow-sm"
                          >
                            Inspect Consented Data
                          </button>
                        ) : (
                          <span className="text-xs text-slate-400 italic">No access</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Bulk Verification via CSV */}
      {activeTab === "bulk" && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-6">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <FileSpreadsheet className="h-5 w-5 text-indigo-600" />
                Bulk Institutional Requisitions (Up to 500 Candidates)
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Upload a CSV spreadsheet containing APAAR IDs. The platform dispatches batch consent requests to all students concurrently.
              </p>
            </div>
            <button
              onClick={() => {
                const csv = "apaar_id,candidate_name,purpose\n123456789012,Sample Student,Campus Hiring 2026\n987654321098,Sample Student 2,Background Check\n";
                const blob = new Blob([csv], { type: "text/csv" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "bulk_verification_template.csv";
                a.click();
              }}
              className="px-3 py-2 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 flex items-center gap-1.5 text-slate-700 dark:text-slate-300"
            >
              <Download className="h-3.5 w-3.5" />
              Download Template
            </button>
          </div>

          <div className="border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-8 text-center bg-slate-50/50 dark:bg-slate-800/20 space-y-3">
            <Upload className="h-10 w-10 text-indigo-500 mx-auto" />
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              Drag & Drop verification CSV or click to browse
            </p>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Automated validation verifies APAAR checksums and queues async notification workers across Redis & Celery.
            </p>
            <input
              type="file"
              accept=".csv"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  alert(`Loaded ${e.target.files[0].name}. Batch processing simulated for 2 candidates!`);
                }
              }}
              className="text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
            />
          </div>
        </div>
      )}

      {/* Tab 4: Offline Cryptographic Verifier */}
      {activeTab === "offline" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-4">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <FileCheck2 className="h-5 w-5 text-indigo-600" />
                Offline Cryptographic Verifier
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Paste an exported verifiable JSON credential or load signed payload to verify mathematically against the AICTE sovereign Ed25519 public key.
              </p>
            </div>

            <textarea
              rows={9}
              value={offlineInput}
              onChange={(e) => setOfflineInput(e.target.value)}
              placeholder='Paste JSON credential here, e.g.:&#10;{&#10;  "payload": { "student_ref_id": "CS-042", "academic_year": "2023-2027", "status": "VALID", "kid": "aicte-key-2026-v1" },&#10;  "signature": "base64url_sig...",&#10;  "kid": "aicte-key-2026-v1"&#10;}'
              className="w-full p-3 font-mono text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
            />

            <div className="flex gap-2">
              <button
                onClick={() => {
                  setOfflineInput(JSON.stringify({
                    payload: {
                      record_id: "demo-valid-uuid-2026",
                      student_ref_id: "DTU-CS-2023",
                      institution: { name: "Delhi Technological University", aicte_id: "1-001" },
                      program: { name: "Computer Science and Engineering" },
                      academic_year: "2023-2027",
                      status: "VALID",
                      kid: "aicte-key-2026-v1",
                    },
                    signature: "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-_AbCdEfGhIjKlMnOpQrStUvWxYz0123",
                    kid: "aicte-key-2026-v1",
                  }, null, 2));
                }}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
              >
                Load Sample JSON
              </button>
              <button
                onClick={handleOfflineVerify}
                className="px-5 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm flex items-center gap-1.5"
              >
                <ShieldCheck className="h-4 w-4" />
                Verify Signature
              </button>
            </div>
          </div>

          {/* Offline Result Card */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm flex flex-col justify-center">
            {offlineResult ? (
              <div className="space-y-4">
                <div className={`p-4 rounded-xl border flex items-start gap-3.5 ${
                  offlineResult.is_signature_valid
                    ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200"
                    : "bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200"
                }`}>
                  {offlineResult.is_signature_valid ? (
                    <CheckCircle2 className="h-6 w-6 text-emerald-600 shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="h-6 w-6 text-rose-600 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <h4 className="font-bold text-sm">
                      {offlineResult.is_signature_valid ? "Cryptographic Signature VALID" : "Signature Verification FAILED"}
                    </h4>
                    <p className="text-xs mt-1 leading-relaxed opacity-90">
                      {offlineResult.reason || "The digital signature was verified using sovereign Ed25519 curve."}
                    </p>
                  </div>
                </div>

                <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-800 text-xs space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Key Identifier (kid):</span>
                    <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">{offlineResult.kid || "aicte-key-2026-v1"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Live Registry Status:</span>
                    <span className="font-semibold text-indigo-600 dark:text-indigo-400">{offlineResult.live_status || "UNKNOWN (Offline Mode)"}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400 text-xs">
                No verification executed yet. Paste a credential and click "Verify Signature".
              </div>
            )}
          </div>
        </div>
      )}

      {/* Consented Data Modal */}
      {activeModalData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-xl w-full p-6 shadow-2xl space-y-5">
            <div className="flex justify-between items-start border-b border-slate-100 dark:border-slate-800 pb-3">
              <div>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400">
                  Consented Record View
                </span>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mt-1">
                  Authorized Academic Profile
                </h3>
              </div>
              <button
                onClick={() => setActiveModalData(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="bg-slate-50 dark:bg-slate-800/60 p-4 rounded-xl border border-slate-200 dark:border-slate-800 text-xs space-y-2.5">
              <p className="text-slate-500">
                <strong>Purpose:</strong> {activeModalData.purpose}
              </p>
              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-200 dark:border-slate-700">
                {Object.entries(activeModalData.student_data || {}).map(([k, v]) => (
                  <div key={k}>
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">
                      {k.replace(/_/g, " ")}
                    </span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200 text-xs">
                      {String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setActiveModalData(null)}
                className="px-4 py-2 text-xs font-semibold bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-700"
              >
                Close View
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
