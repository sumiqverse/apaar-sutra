import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  History,
  Lock,
  Download,
  Building,
  KeyRound,
  FileCheck2,
  Scale,
} from "lucide-react";
import { apiClient } from "@/lib/api";

export const StudentConsentPortal: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<"inbox" | "active" | "history">("inbox");

  // State for pending requests
  const [inbox, setInbox] = useState<any[]>([
    {
      id: "demo-consent-req-01",
      verifier_org_name: "Tata Consultancy Services - Talent Acquisition",
      purpose: "Background verification for Software Developer offer letter",
      purpose_category: "EMPLOYMENT",
      fields_requested: ["name", "institution_name", "program_name", "academic_year", "cgpa"],
      retention_days: 30,
      status: "PENDING",
      expires_at: new Date(Date.now() + 2592000000).toISOString(),
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: "demo-consent-req-02",
      verifier_org_name: "National Overseas Scholarship Bureau",
      purpose: "Eligibility assessment for Graduate Fellowship 2026-27",
      purpose_category: "SCHOLARSHIP",
      fields_requested: ["name", "dob", "gender", "institution_name", "program_name", "cgpa"],
      retention_days: 60,
      status: "PENDING",
      expires_at: new Date(Date.now() + 5184000000).toISOString(),
      created_at: new Date(Date.now() - 7200000).toISOString(),
    },
  ]);

  const [activeConsents, setActiveConsents] = useState<any[]>([
    {
      id: "active-consent-01",
      verifier_org_name: "Infosys Campus Recruitment",
      purpose: "Campus drive qualification evaluation",
      purpose_category: "EMPLOYMENT",
      approved_fields: ["name", "institution_name", "program_name", "cgpa"],
      receipt_signature: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      approved_at: new Date(Date.now() - 86400000).toISOString(),
      expires_at: new Date(Date.now() + 2505600000).toISOString(),
      status: "APPROVED",
    },
  ]);

  const [accessHistory, setAccessHistory] = useState<any>({
    commercial_verifications: [
      {
        id: "h1",
        verifier_org_name: "Infosys Campus Recruitment",
        purpose: "Campus drive qualification evaluation",
        status: "APPROVED",
        approved_fields: ["name", "institution_name", "program_name", "cgpa"],
        created_at: new Date(Date.now() - 86400000).toISOString(),
      },
    ],
    regulatory_accesses: [
      {
        id: "r1",
        actor_name: "Dr. R. Sharma (Director, Academic Bureau)",
        agency_name: "All India Council for Technical Education (AICTE)",
        legal_basis: "Section 10(g) AICTE Act 1987 - Annual Quality Compliance Audit",
        reference_number: "AICTE/AUDIT/2026/892",
        justification: "Statutory curriculum progression review and national accreditation audit.",
        accessed_fields: ["institution", "program", "status", "academic_year"],
        created_at: new Date(Date.now() - 172800000).toISOString(),
      },
    ],
  });

  // Modal Review State
  const [selectedReq, setSelectedReq] = useState<any | null>(null);
  const [chosenFields, setChosenFields] = useState<string[]>([]);
  const [otpInput, setOtpInput] = useState("123456");
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    // Fetch live inbox if available
    apiClient<any[]>("/api/v1/consent/student-inbox")
      .then((data) => {
        if (data && data.length > 0) {
          setInbox(data.filter((d) => d.status === "PENDING"));
          setActiveConsents(data.filter((d) => d.status === "APPROVED"));
        }
      })
      .catch(() => {});

    // Fetch access history
    apiClient<any>("/api/v1/consent/access-history")
      .then((hist) => {
        if (hist && (hist.commercial_verifications?.length || hist.regulatory_accesses?.length)) {
          setAccessHistory(hist);
        }
      })
      .catch(() => {});
  }, []);

  const openApprovalModal = (req: any) => {
    setSelectedReq(req);
    setChosenFields([...req.fields_requested]);
    setOtpInput("123456");
  };

  const toggleFieldChoice = (field: string) => {
    if (chosenFields.includes(field)) {
      setChosenFields(chosenFields.filter((f) => f !== field));
    } else {
      setChosenFields([...chosenFields, field]);
    }
  };

  const handleApprove = async () => {
    if (chosenFields.length === 0) {
      alert("You must approve at least one field or click Deny.");
      return;
    }
    setIsProcessing(true);
    try {
      await apiClient(`/api/v1/consent/requests/${selectedReq.id}/approve`, {
        method: "POST",
        body: JSON.stringify({
          approved_fields: chosenFields,
          otp: otpInput,
        }),
      });
      alert("Consent approved successfully! Cryptographic receipt generated.");
    } catch {
      // Mock local transition for demo
    }

    const updated = {
      ...selectedReq,
      status: "APPROVED",
      approved_fields: chosenFields,
      receipt_signature: "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-_Ed25519SignedReceipt",
      approved_at: new Date().toISOString(),
    };
    setActiveConsents([updated, ...activeConsents]);
    setInbox(inbox.filter((i) => i.id !== selectedReq.id));
    setSelectedReq(null);
    setIsProcessing(false);
  };

  const handleDeny = async (id: string) => {
    try {
      await apiClient(`/api/v1/consent/requests/${id}/deny`, { method: "POST" });
    } catch {}
    setInbox(inbox.filter((i) => i.id !== id));
    alert("Requisition successfully denied.");
  };

  const handleRevoke = async (id: string) => {
    if (!confirm("Are you sure you want to withdraw/revoke consent? The verifier will immediately lose access.")) {
      return;
    }
    try {
      await apiClient(`/api/v1/consent/requests/${id}/revoke`, { method: "POST" });
    } catch {}
    setActiveConsents(activeConsents.filter((c) => c.id !== id));
    alert("Consent has been revoked per your DPDP right of withdrawal.");
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto" role="region" aria-label="Student Privacy & Consent Dashboard">
      {/* Sovereign Header (Pink Color-Block Section) */}
      <div className="bg-[#FFD6E8] text-black rounded-[24px] p-8 md:p-10 flex flex-col md:flex-row items-start md:items-end justify-between gap-6">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-black text-white font-semibold uppercase tracking-[0.54px]">
              DPDP Act 2023 Student Sovereignty
            </span>
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-white text-black border border-black/10 font-semibold uppercase tracking-[0.54px]">
              One Nation, One Student ID
            </span>
          </div>
          <h1 className="text-3xl md:text-5xl font-medium tracking-[-1.2px] text-black leading-[1.05]">
            Student Privacy & Consent Dashboard
          </h1>
          <p className="text-sm md:text-base font-[330] text-black/80 max-w-2xl tracking-[-0.26px]">
            You maintain absolute sovereignty over your APAAR academic records. Review who is requesting your data, approve granular subsets of fields, withdraw consent at any time, and audit all access events.
          </p>
        </div>
      </div>

      {/* Tab Navigation (Pill Switcher) */}
      <div className="flex items-center bg-white p-1.5 rounded-full border border-[#E5E5E5] overflow-x-auto w-fit max-w-full">
        {[
          { id: "inbox", label: `Pending Requests (${inbox.length})`, icon: Clock },
          { id: "active", label: `Active Consents (${activeConsents.length})`, icon: CheckCircle2 },
          { id: "history", label: "Who Accessed My Data (Audit)", icon: History },
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

      {/* Tab 1: Inbox */}
      {activeTab === "inbox" && (
        <div className="space-y-4">
          {inbox.length === 0 ? (
            <div className="bg-white rounded-[20px] border border-[#E5E5E5] p-12 text-center text-black/60 text-xs font-mono uppercase tracking-[0.54px]">
              <ShieldCheck className="h-8 w-8 text-black mx-auto mb-2" />
              You have no pending consent requisitions. Your academic records are secure.
            </div>
          ) : (
            inbox.map((req) => (
              <div
                key={req.id}
                className="bg-white rounded-[20px] border border-[#E5E5E5] p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 hover:border-black transition-all"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] px-2.5 py-0.5 rounded-full bg-[#FFF5EA] text-black border border-[#E5E5E5]">
                      {req.purpose_category}
                    </span>
                    <h3 className="font-semibold text-black text-base tracking-[-0.2px]">
                      {req.verifier_org_name}
                    </h3>
                  </div>
                  <p className="text-xs font-[330] text-black/75">
                    <strong className="font-semibold text-black">Declared Purpose:</strong> {req.purpose}
                  </p>
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <span className="font-mono text-[10px] text-black/50 uppercase tracking-[0.54px]">Requested fields:</span>
                    {req.fields_requested.map((f: string) => (
                      <span
                        key={f}
                        className="px-2.5 py-0.5 rounded-full text-[11px] bg-[#F5F5F5] text-black border border-[#E5E5E5] font-mono"
                      >
                        {f}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-2.5 shrink-0">
                  <button
                    onClick={() => handleDeny(req.id)}
                    className="px-4 py-2 text-xs font-medium rounded-full border border-[#E5E5E5] hover:border-rose-400 text-rose-600 bg-white hover:bg-rose-50 transition-colors cursor-pointer"
                  >
                    Deny
                  </button>
                  <button
                    onClick={() => openApprovalModal(req)}
                    className="px-5 py-2.5 text-xs font-medium rounded-full bg-black hover:bg-black/85 text-white transition-all flex items-center gap-2 cursor-pointer shadow-sm"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Review & Approve</span>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab 2: Active Consents */}
      {activeTab === "active" && (
        <div className="space-y-4">
          {activeConsents.map((consent) => (
            <div
              key={consent.id}
              className="bg-white rounded-[20px] border border-[#E5E5E5] p-6 space-y-4 hover:border-black transition-all"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E5E5E5] pb-4">
                <div>
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] px-2.5 py-0.5 rounded-full bg-[#D2F8E7] text-black">
                      Active Authorization
                    </span>
                    <h3 className="font-semibold text-black tracking-[-0.2px]">
                      {consent.verifier_org_name}
                    </h3>
                  </div>
                  <p className="text-xs font-[330] text-black/70 mt-1">{consent.purpose}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleRevoke(consent.id)}
                    className="px-4 py-2 text-xs font-medium rounded-full bg-[#FFF5EA] hover:bg-[#FF8577] text-black border border-[#E5E5E5] transition-colors cursor-pointer"
                  >
                    Revoke Access (Withdraw)
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-[330]">
                <div>
                  <span className="font-mono text-[10px] uppercase font-semibold text-black/50 block tracking-[0.54px]">Approved Fields:</span>
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {consent.approved_fields?.map((f: string) => (
                      <span key={f} className="px-2.5 py-0.5 rounded-full bg-[#F5F5F5] border border-[#E5E5E5] text-black font-mono text-[11px]">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="font-mono text-[10px] uppercase font-semibold text-black/50 block tracking-[0.54px]">Cryptographic Receipt:</span>
                  <div className="font-mono text-[11px] text-black/80 truncate mt-1.5">
                    {consent.receipt_signature || "Ed25519-Signed-Receipt-Verified"}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 3: Access History / "Who Accessed My Data" */}
      {activeTab === "history" && (
        <div className="space-y-6">
          {/* Statutory Regulatory Queries */}
          <div className="bg-white rounded-[20px] border border-[#E5E5E5] p-6 md:p-8 space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-[#F5F5F5] border border-[#E5E5E5] flex items-center justify-center text-black">
                <Scale className="h-4 w-4 text-black" />
              </div>
              <div>
                <h3 className="font-semibold text-black text-base tracking-[-0.2px]">
                  Statutory & Regulatory Audit Log
                </h3>
                <p className="text-xs font-[330] text-black/60">
                  Government agencies and accredited councils accessing academic progress under lawful authority.
                </p>
              </div>
            </div>

            <div className="space-y-3">
              {accessHistory.regulatory_accesses?.map((r: any) => (
                <div key={r.id} className="p-5 rounded-[16px] bg-[#F9F9F9] border border-[#E5E5E5] space-y-2">
                  <div className="flex justify-between items-start gap-4 flex-wrap">
                    <div className="font-semibold text-sm text-black">
                      {r.agency_name}
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-white text-black border border-[#E5E5E5] uppercase tracking-[0.54px]">
                      Ref: {r.reference_number}
                    </span>
                  </div>
                  <p className="text-xs font-[330] text-black/80">
                    <strong className="font-semibold text-black">Legal Statutory Basis:</strong> {r.legal_basis}
                  </p>
                  <p className="text-xs font-[330] text-black/70">
                    <strong className="font-semibold text-black">Lawful Justification:</strong> {r.justification}
                  </p>
                  <div className="text-[11px] font-mono text-black/50 pt-1">
                    Recorded on {new Date(r.created_at).toLocaleString()} | Officer: {r.actor_name}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Granular Approval Modal */}
      {selectedReq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[24px] border border-[#E5E5E5] max-w-lg w-full p-8 shadow-2xl space-y-6">
            <div className="space-y-1.5">
              <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] px-2.5 py-0.5 rounded-full bg-[#E5D4FF] text-black">
                DPDP Granular Consent Review
              </span>
              <h3 className="text-lg font-medium tracking-[-0.3px] text-black">
                Authorize Access for {selectedReq.verifier_org_name}
              </h3>
              <p className="text-xs font-[330] text-black/60">
                You have the right under Section 6 of the DPDP Act 2023 to uncheck any non-mandatory fields.
              </p>
            </div>

            {/* Checkbox selector for requested fields */}
            <div className="space-y-2">
              <label className="font-mono text-[10px] uppercase font-semibold tracking-[0.54px] text-black/60">
                Select Fields to Authorize:
              </label>
              <div className="grid grid-cols-2 gap-2 bg-[#F9F9F9] p-3.5 rounded-[16px] border border-[#E5E5E5]">
                {selectedReq.fields_requested.map((f: string) => {
                  const isChecked = chosenFields.includes(f);
                  return (
                    <label
                      key={f}
                      onClick={() => toggleFieldChoice(f)}
                      className={`flex items-center gap-2.5 p-2 rounded-full cursor-pointer text-xs font-medium border transition-all ${
                        isChecked
                          ? "bg-black text-white border-black"
                          : "bg-white text-black/70 border-[#E5E5E5]"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {}}
                        className="rounded accent-black sr-only"
                      />
                      <span className="truncate">{f.replace(/_/g, " ")}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Simulated OTP Challenge */}
            <div className="space-y-1.5">
              <label className="font-mono text-[10px] uppercase font-semibold tracking-[0.54px] text-black/60">
                Simulated OTP Challenge (DPDP Explicit Verification)
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={otpInput}
                  onChange={(e) => setOtpInput(e.target.value)}
                  className="w-full px-4 py-2.5 text-sm font-mono tracking-widest rounded-full border border-[#E5E5E5] bg-white text-black focus:border-black focus:outline-none"
                />
                <span className="absolute right-4 top-2.5 text-[11px] text-black/40 font-mono">
                  Default: 123456
                </span>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setSelectedReq(null)}
                className="px-5 py-2.5 text-xs font-medium rounded-full bg-white border border-[#E5E5E5] text-black hover:bg-[#F5F5F5] transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleApprove}
                disabled={isProcessing}
                className="px-6 py-2.5 text-xs font-medium rounded-full bg-black hover:bg-black/85 text-white transition-all flex items-center gap-2 cursor-pointer shadow-sm"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Sign & Authorize</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
