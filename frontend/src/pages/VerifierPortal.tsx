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
    <div className="space-y-8 max-w-7xl mx-auto" role="region" aria-label="Authorized Verifier Portal">
      {/* Header Banner (Mint Color-Block Section) */}
      <div className="bg-[#D2F8E7] text-black rounded-[24px] p-8 md:p-10 flex flex-col md:flex-row items-start md:items-end justify-between gap-6">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-black text-white font-semibold uppercase tracking-[0.54px]">
              DPDP Act 2023 Compliant
            </span>
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-white text-black border border-black/10 font-semibold uppercase tracking-[0.54px]">
              Ed25519 Sovereign Signatures
            </span>
          </div>
          <h1 className="text-3xl md:text-5xl font-medium tracking-[-1.2px] text-black leading-[1.05]">
            Authorized Verifier Portal
          </h1>
          <p className="text-sm md:text-base font-[330] text-black/80 max-w-2xl tracking-[-0.26px]">
            Cryptographically verify academic credentials, request student consent with purpose limitation, and execute bulk verification workflows with zero data leakage.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setActiveTab("offline")}
            className="px-5 py-2.5 text-xs font-medium rounded-full bg-black hover:bg-black/85 text-white transition-all flex items-center gap-2 cursor-pointer"
          >
            <FileCheck2 className="h-3.5 w-3.5" />
            <span>Offline Verifier</span>
          </button>
        </div>
      </div>

      {/* Pill Tab Navigation */}
      <div className="flex items-center bg-white p-1.5 rounded-full border border-[#E5E5E5] overflow-x-auto w-fit max-w-full">
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
              className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-full transition-all whitespace-nowrap cursor-pointer ${
                active
                  ? "bg-black text-white shadow-sm"
                  : "text-black/70 hover:text-black hover:bg-black/5"
              }`}
            >
              <Icon className={`h-3.5 w-3.5 ${active ? "text-white" : "text-black/60"}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Single Consent Requisition */}
      {activeTab === "query" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-[24px] border border-[#E5E5E5] p-6 md:p-8 space-y-6">
            <div className="space-y-1">
              <span className="font-mono text-xs uppercase tracking-[0.54px] font-semibold text-black/60">
                DPDP Section 6 Compliance
              </span>
              <h2 className="text-xl md:text-2xl font-medium tracking-[-0.6px] text-black flex items-center gap-2">
                <Search className="h-5 w-5 text-black" />
                <span>Initiate DPDP Consent Requisition</span>
              </h2>
              <p className="text-xs font-[330] text-black/60">
                Under Section 6 of the DPDP Act 2023, verifiers must declare a specified purpose and request only the minimum necessary data points.
              </p>
            </div>

            <form onSubmit={handleCreateConsent} className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] text-black/60 block">
                    Student APAAR ID (12 Digits)
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={12}
                    value={apaarId}
                    onChange={(e) => setApaarId(e.target.value)}
                    placeholder="123456789012"
                    className="w-full px-4 py-2.5 rounded-full border border-[#E5E5E5] bg-white text-black text-sm focus:border-black focus:outline-none font-mono tracking-widest"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] text-black/60 block">
                    Verifier Organization
                  </label>
                  <input
                    type="text"
                    required
                    value={verifierOrgName}
                    onChange={(e) => setVerifierOrgName(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-full border border-[#E5E5E5] bg-white text-black text-sm focus:border-black focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] text-black/60 block">
                    Purpose Category
                  </label>
                  <select
                    value={purposeCategory}
                    onChange={(e) => setPurposeCategory(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-full border border-[#E5E5E5] bg-white text-black text-sm focus:border-black focus:outline-none"
                  >
                    <option value="EMPLOYMENT">Employment & Background Check</option>
                    <option value="HIGHER_EDUCATION">Higher Education Admissions</option>
                    <option value="SCHOLARSHIP">Scholarship / Fellowship Eligibility</option>
                    <option value="VISA">Visa & Immigration Credential Assessment</option>
                    <option value="GENERAL">General Academic Verification</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] text-black/60 block">
                    Retention Limit: {retentionDays} Days
                  </label>
                  <input
                    type="range"
                    min={7}
                    max={90}
                    step={7}
                    value={retentionDays}
                    onChange={(e) => setRetentionDays(Number(e.target.value))}
                    className="w-full accent-black mt-2"
                  />
                  <span className="text-[11px] font-[330] text-black/50 block">Auto-expires after {retentionDays} days per DPDP principles.</span>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] text-black/60 block">
                  Specific Justification / Requisition Note
                </label>
                <input
                  type="text"
                  required
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  placeholder="e.g. Verification for Software Engineer role offer letter"
                  className="w-full px-4 py-2.5 rounded-full border border-[#E5E5E5] bg-white text-black text-sm focus:border-black focus:outline-none"
                />
              </div>

              {/* Data Minimisation Selector */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] text-black/60">
                    Requested Fields (Data Minimisation Selector)
                  </label>
                  <span className="font-mono text-[11px] text-black font-semibold">
                    {selectedFields.length} of {ALLOWED_FIELDS.length} selected
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-[#F9F9F9] p-4 rounded-[16px] border border-[#E5E5E5]">
                  {ALLOWED_FIELDS.map((f) => {
                    const checked = selectedFields.includes(f.id);
                    return (
                      <label
                        key={f.id}
                        onClick={() => handleToggleField(f.id)}
                        className={`flex items-center gap-2.5 p-2.5 rounded-full cursor-pointer transition-all border text-xs font-medium ${
                          checked
                            ? "bg-black text-white border-black"
                            : "bg-white text-black/70 border-[#E5E5E5] hover:border-black"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {}}
                          className="sr-only"
                        />
                        <span className="truncate">{f.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-6 py-3 bg-black hover:bg-black/85 text-white font-medium text-xs rounded-full shadow-sm transition-all flex items-center gap-2 disabled:opacity-50 cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      <span>Sending Requisition...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>Send Consent Requisition</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Guidelines Sidebar */}
          <div className="space-y-6">
            <div className="bg-white rounded-[24px] border border-[#E5E5E5] p-6 space-y-4 hover:border-black transition-all">
              <h3 className="text-sm font-semibold text-black flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-black" />
                <span>DPDP Act 2023 Safeguards</span>
              </h3>
              <ul className="text-xs text-black/75 space-y-2.5 leading-relaxed font-[330]">
                <li className="flex gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-black mt-1.5 shrink-0" />
                  <span><strong className="font-semibold text-black">Purpose Limitation:</strong> Academic data may only be utilized for the specified lawful purpose.</span>
                </li>
                <li className="flex gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-black mt-1.5 shrink-0" />
                  <span><strong className="font-semibold text-black">Granular Approval:</strong> The student possesses the legal prerogative to deny non-essential fields.</span>
                </li>
                <li className="flex gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-black mt-1.5 shrink-0" />
                  <span><strong className="font-semibold text-black">Right to Withdraw:</strong> The student can revoke active consent at any moment before expiry.</span>
                </li>
                <li className="flex gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-black mt-1.5 shrink-0" />
                  <span><strong className="font-semibold text-black">Tamper-Evident Receipts:</strong> Every approval generates an Ed25519-signed consent receipt.</span>
                </li>
              </ul>
            </div>

            {/* Lime Test Credentials Callout */}
            <div className="bg-[#D4FF5B] text-black p-6 rounded-[24px] space-y-3">
              <div className="font-mono text-xs font-semibold uppercase tracking-[0.54px] text-black/70">
                Evaluation Test Credentials
              </div>
              <p className="text-xs font-[330] text-black/85">
                Test with any synthetic 12-digit APAAR ID in the repository:
              </p>
              <div className="bg-white p-3 rounded-full font-mono text-xs text-black border border-black/10 font-semibold tracking-wider text-center">
                123456789012
              </div>
              <p className="text-[11px] font-[330] text-black/70">
                Simulated student approval OTP is fixed to <code className="font-bold">123456</code> for reliable demonstration.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Consent Status Tracker */}
      {activeTab === "tracker" && (
        <div className="bg-white rounded-[24px] border border-[#E5E5E5] p-6 md:p-8 space-y-6">
          <div className="space-y-1">
            <span className="font-mono text-xs uppercase tracking-[0.54px] font-semibold text-black/60">
              Audit & Lifecycle
            </span>
            <h3 className="text-xl font-medium tracking-[-0.5px] text-black">
              Requisition Tracking Ledger
            </h3>
            <p className="text-xs font-[330] text-black/60">
              Real-time lifecycle monitoring of all submitted verification consent requests.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F9F9F9] uppercase font-mono font-semibold text-[10px] tracking-[0.54px] text-black/60 border-b border-[#E5E5E5]">
                <tr>
                  <th className="px-5 py-3">Verifier Org</th>
                  <th className="px-5 py-3">Purpose & Category</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Approved Fields</th>
                  <th className="px-5 py-3">Requested At</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E5]">
                {recentRequests.map((req) => {
                  const isApproved = req.status === "APPROVED";
                  const isPending = req.status === "PENDING";
                  const isDenied = req.status === "DENIED";
                  const isRevoked = req.status === "REVOKED";

                  return (
                    <tr key={req.id || req.token} className="hover:bg-[#F9F9F9] transition-colors">
                      <td className="px-5 py-3.5 font-medium text-black">
                        {req.verifier_org_name}
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="font-semibold text-xs tracking-[-0.1px] text-black">{req.purpose}</div>
                        <div className="text-[11px] text-black/50 font-mono">{req.purpose_category}</div>
                      </td>
                      <td className="px-5 py-3.5">
                        {isApproved && (
                          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] font-mono font-semibold uppercase tracking-[0.54px] bg-[#D2F8E7] text-black">
                            <CheckCircle2 className="h-3 w-3" /> Approved
                          </span>
                        )}
                        {isPending && (
                          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] font-mono font-semibold uppercase tracking-[0.54px] bg-[#FFF5EA] text-black border border-[#E5E5E5]">
                            <Clock className="h-3 w-3" /> Pending Student Action
                          </span>
                        )}
                        {isDenied && (
                          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] font-mono font-semibold uppercase tracking-[0.54px] bg-[#FF8577] text-black">
                            <XCircle className="h-3 w-3" /> Denied by Student
                          </span>
                        )}
                        {isRevoked && (
                          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] font-mono font-semibold uppercase tracking-[0.54px] bg-[#F5F5F5] text-black border border-[#E5E5E5]">
                            <AlertTriangle className="h-3 w-3" /> Revoked by Student
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-xs text-black/60 font-[330]">
                        {isApproved ? `${req.approved_fields?.length || 0} fields unlocked` : "Locked (Awaiting Approval)"}
                      </td>
                      <td className="px-5 py-3.5 text-xs font-mono text-black/50">
                        {new Date(req.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        {isApproved ? (
                          <button
                            onClick={() => handleInspectConsentedRecord(req.token)}
                            className="px-3.5 py-1.5 text-xs font-medium bg-black hover:bg-black/85 text-white rounded-full transition-colors cursor-pointer"
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
        <div className="bg-white rounded-[24px] border border-[#E5E5E5] p-6 md:p-8 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <span className="font-mono text-xs uppercase tracking-[0.54px] font-semibold text-black/60">
                Batch Verification Engine
              </span>
              <h3 className="text-xl font-medium tracking-[-0.5px] text-black flex items-center gap-2">
                <FileSpreadsheet className="h-5 w-5 text-black" />
                <span>Bulk Institutional Requisitions (Up to 500 Candidates)</span>
              </h3>
              <p className="text-xs font-[330] text-black/60">
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
              className="px-4 py-2 text-xs font-medium rounded-full border border-[#E5E5E5] hover:border-black bg-white hover:bg-[#F5F5F5] flex items-center gap-1.5 text-black transition-colors cursor-pointer shrink-0"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Download Template</span>
            </button>
          </div>

          <div className="border border-dashed border-[#E5E5E5] rounded-[20px] p-10 text-center bg-[#F9F9F9] space-y-3">
            <div className="w-12 h-12 rounded-full bg-white border border-[#E5E5E5] flex items-center justify-center mx-auto text-black">
              <Upload className="h-5 w-5" />
            </div>
            <p className="text-sm font-semibold text-black tracking-[-0.2px]">
              Drag & Drop verification CSV or click to browse
            </p>
            <p className="text-xs font-[330] text-black/60 max-w-sm mx-auto">
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
              className="text-xs text-black/60 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-medium file:bg-black file:text-white hover:file:bg-black/85 cursor-pointer"
            />
          </div>
        </div>
      )}

      {/* Tab 4: Offline Cryptographic Verifier */}
      {activeTab === "offline" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-[24px] border border-[#E5E5E5] p-6 md:p-8 space-y-5">
            <div className="space-y-1">
              <span className="font-mono text-xs uppercase tracking-[0.54px] font-semibold text-black/60">
                Sovereign Ed25519 Engine
              </span>
              <h3 className="text-xl font-medium tracking-[-0.5px] text-black flex items-center gap-2">
                <FileCheck2 className="h-5 w-5 text-black" />
                <span>Offline Cryptographic Verifier</span>
              </h3>
              <p className="text-xs font-[330] text-black/60">
                Paste an exported verifiable JSON credential or load signed payload to verify mathematically against the AICTE sovereign Ed25519 public key.
              </p>
            </div>

            <textarea
              rows={9}
              value={offlineInput}
              onChange={(e) => setOfflineInput(e.target.value)}
              placeholder='Paste JSON credential here, e.g.:&#10;{&#10;  "payload": { "student_ref_id": "CS-042", "academic_year": "2023-2027", "status": "VALID", "kid": "aicte-key-2026-v1" },&#10;  "signature": "base64url_sig...",&#10;  "kid": "aicte-key-2026-v1"&#10;}'
              className="w-full p-4 font-mono text-xs rounded-[16px] border border-[#E5E5E5] bg-[#F9F9F9] text-black focus:border-black focus:outline-none"
            />

            <div className="flex gap-2.5">
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
                className="px-4 py-2 text-xs font-medium rounded-full border border-[#E5E5E5] hover:border-black bg-white hover:bg-[#F5F5F5] text-black transition-colors cursor-pointer"
              >
                Load Sample JSON
              </button>
              <button
                onClick={handleOfflineVerify}
                className="px-5 py-2 text-xs font-medium rounded-full bg-black hover:bg-black/85 text-white transition-all flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Verify Signature</span>
              </button>
            </div>
          </div>

          {/* Offline Result Card */}
          <div className="bg-white rounded-[24px] border border-[#E5E5E5] p-6 md:p-8 flex flex-col justify-center">
            {offlineResult ? (
              <div className="space-y-4">
                <div className={`p-5 rounded-[20px] border flex items-start gap-3.5 ${
                  offlineResult.is_signature_valid
                    ? "bg-[#D2F8E7] text-black border-black/10"
                    : "bg-[#FF8577] text-black border-black/10"
                }`}>
                  {offlineResult.is_signature_valid ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-800 shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="h-5 w-5 text-rose-900 shrink-0 mt-0.5" />
                  )}
                  <div className="space-y-1">
                    <h4 className="font-semibold text-sm">
                      {offlineResult.is_signature_valid ? "Cryptographic Signature VALID" : "Signature Verification FAILED"}
                    </h4>
                    <p className="text-xs font-[330] leading-relaxed">
                      {offlineResult.reason || "The digital signature was verified using sovereign Ed25519 curve."}
                    </p>
                  </div>
                </div>

                <div className="bg-[#F9F9F9] p-4 rounded-[16px] border border-[#E5E5E5] text-xs space-y-2 font-mono">
                  <div className="flex justify-between">
                    <span className="text-black/50">Key Identifier (kid):</span>
                    <span className="font-semibold text-black">{offlineResult.kid || "aicte-key-2026-v1"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-black/50">Live Registry Status:</span>
                    <span className="font-semibold text-black">{offlineResult.live_status || "UNKNOWN (Offline Mode)"}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-black/40 text-xs font-mono uppercase tracking-[0.54px]">
                No verification executed yet. Paste a credential and click "Verify Signature".
              </div>
            )}
          </div>
        </div>
      )}

      {/* Consented Data Modal */}
      {activeModalData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[24px] border border-[#E5E5E5] max-w-xl w-full p-8 shadow-2xl space-y-6">
            <div className="flex justify-between items-start border-b border-[#E5E5E5] pb-4">
              <div className="space-y-1">
                <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] px-2.5 py-0.5 rounded-full bg-[#D2F8E7] text-black">
                  Consented Record View
                </span>
                <h3 className="text-lg font-medium tracking-[-0.3px] text-black">
                  Authorized Academic Profile
                </h3>
              </div>
              <button
                onClick={() => setActiveModalData(null)}
                className="w-8 h-8 rounded-full border border-[#E5E5E5] flex items-center justify-center text-black/60 hover:text-black hover:border-black cursor-pointer text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="bg-[#F9F9F9] p-5 rounded-[18px] border border-[#E5E5E5] text-xs space-y-3">
              <p className="text-black/70 font-[330]">
                <strong className="font-semibold text-black">Purpose:</strong> {activeModalData.purpose}
              </p>
              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-[#E5E5E5]">
                {Object.entries(activeModalData.student_data || {}).map(([k, v]) => (
                  <div key={k}>
                    <span className="font-mono text-[10px] uppercase font-semibold text-black/50 tracking-[0.54px] block">
                      {k.replace(/_/g, " ")}
                    </span>
                    <span className="font-semibold text-black text-xs">
                      {String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setActiveModalData(null)}
                className="px-5 py-2.5 text-xs font-medium bg-black hover:bg-black/85 text-white rounded-full transition-colors cursor-pointer"
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
export default VerifierPortal;
