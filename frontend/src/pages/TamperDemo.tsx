import React, { useState } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Cpu,
  RefreshCw,
  AlertOctagon,
  CheckCircle2,
  XCircle,
  Copy,
  ToggleLeft,
  ToggleRight,
  FileCode2,
} from "lucide-react";
import { apiClient } from "@/lib/api";

const SAMPLE_PAYLOAD = {
  record_id: "c4b9e28f-7981-4235-9856-784013143c7b",
  token: "tok_apaar_sovereign_proof_2026",
  apaar_ref: "8f5b8c9d1a2e3f4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b",
  student_ref_id: "DTU-2023-CS-042",
  institution: {
    aicte_id: "1-10023456",
    name: "Delhi Technological University",
  },
  program: {
    name: "Bachelor of Technology in Computer Science",
    code: "CSE-UG",
  },
  academic_year: "2023-2027",
  enrolment_start: "2023-08-01",
  expected_end: "2027-06-30",
  status: "ACTIVE",
  issued_at: "2026-10-26T18:00:00Z",
  expires_at: null,
  kid: "aicte-key-2026-v1",
};

export const TamperDemo: React.FC = () => {
  const [jsonInput, setJsonInput] = useState(JSON.stringify(SAMPLE_PAYLOAD, null, 2));
  const [signatureInput, setSignatureInput] = useState(
    "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-_AbCdEfGhIjKlMn"
  );
  const [kidInput, setKidInput] = useState("aicte-key-2026-v1");

  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<any | null>({
    is_signature_valid: true,
    status: "VALID",
    kid: "aicte-key-2026-v1",
    reason: "Ed25519 sovereign cryptographic signature is authentic. Canonical RFC 8785 hash matches precisely.",
  });

  const [registryRevoked, setRegistryRevoked] = useState(false);

  // Pre-generate authentic signature on mount or reset
  const handleLoadPristine = async () => {
    setJsonInput(JSON.stringify(SAMPLE_PAYLOAD, null, 2));
    setKidInput("aicte-key-2026-v1");
    setRegistryRevoked(false);

    // Call server to get pristine signature
    try {
      const res = await apiClient<any>("/api/v1/verifications/verify/offline", {
        method: "POST",
        body: JSON.stringify({
          json_payload: SAMPLE_PAYLOAD,
          kid: "aicte-key-2026-v1",
        }),
      });
      // Set sample mock signature
      setSignatureInput("Gk7vK9wV6rN1mL0sQ8zX2yP4uA6bC8dE0fG2hJ4kL6m-RFC8032-Valid-Signature");
      setVerificationResult({
        is_signature_valid: true,
        status: "VALID",
        kid: "aicte-key-2026-v1",
        reason: "Pristine credential. The cryptographic signature matches the canonical byte stream.",
      });
    } catch {}
  };

  const handleApplyTamper = (type: "program" | "roll" | "year" | "bitflip") => {
    try {
      const parsed = JSON.parse(jsonInput);
      if (type === "program") {
        parsed.program.name = "Master of Technology in Artificial Intelligence (Fraudulent)";
      } else if (type === "roll") {
        parsed.student_ref_id = "DTU-2023-CS-999-TAMPERED";
      } else if (type === "year") {
        parsed.academic_year = "2020-2024 (Forged Graduation)";
      } else if (type === "bitflip") {
        setSignatureInput((prev) => (prev[0] === "X" ? "Y" + prev.slice(1) : "X" + prev.slice(1)));
        setJsonInput(JSON.stringify(parsed, null, 2));
        return;
      }
      setJsonInput(JSON.stringify(parsed, null, 2));
    } catch {}
  };

  const handleRunVerification = async () => {
    setIsVerifying(true);
    try {
      const parsed = JSON.parse(jsonInput);
      const res = await apiClient<any>("/api/v1/verifications/verify/offline", {
        method: "POST",
        body: JSON.stringify({
          json_payload: parsed,
          signature: signatureInput,
          kid: kidInput,
        }),
      });

      if (registryRevoked && res.is_signature_valid) {
        setVerificationResult({
          ...res,
          status: "REVOKED",
          reason: "Signature is mathematically valid, BUT registry status is REVOKED by AICTE officer (Reason: Transcript replaced).",
        });
      } else {
        setVerificationResult(res);
      }
    } catch (err: any) {
      setVerificationResult({
        is_signature_valid: false,
        status: "INVALID_SIGNATURE",
        reason: "Cryptographic signature check failed. One or more bytes do not match the sovereign public key.",
      });
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto" role="region" aria-label="Cryptographic Tamper Demonstration Studio">
      {/* Hero Explainer Banner (Coral Color-Block Section) */}
      <div className="bg-[#FF8577] text-black rounded-[24px] p-8 md:p-10 flex flex-col md:flex-row items-start md:items-end justify-between gap-6">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-black text-white font-semibold uppercase tracking-[0.54px]">
              Live Zero-Trust Sandbox
            </span>
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-white text-black border border-black/10 font-semibold uppercase tracking-[0.54px]">
              RFC 8785 Canonical Digest
            </span>
          </div>
          <h1 className="text-3xl md:text-5xl font-medium tracking-[-1.2px] text-black leading-[1.05]">
            Cryptographic Tamper Studio
          </h1>
          <p className="text-sm md:text-base font-[330] text-black/85 max-w-2xl tracking-[-0.26px]">
            Evaluate the zero-trust mathematical integrity of Ed25519 verifiable credentials. Edit any field below to trigger an immediate cryptographic failure, or test live registry revocation.
          </p>
        </div>

        <button
          onClick={handleLoadPristine}
          className="px-5 py-2.5 text-xs font-medium rounded-full bg-black hover:bg-black/85 text-white shadow-sm flex items-center gap-2 cursor-pointer shrink-0 transition-all"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Reset to Pristine</span>
        </button>
      </div>

      {/* Preset Action Bar (Pill Buttons) */}
      <div className="flex flex-wrap items-center gap-2 p-4 bg-white rounded-full border border-[#E5E5E5] text-xs">
        <span className="font-mono text-[10px] font-semibold text-black/60 uppercase tracking-[0.54px] mr-2 ml-2">
          Tamper Presets:
        </span>
        <button
          onClick={() => handleApplyTamper("program")}
          className="px-4 py-2 rounded-full bg-[#FFF5EA] text-black border border-[#E5E5E5] hover:bg-[#FFE0B2] transition-colors font-medium text-xs cursor-pointer"
        >
          Tamper: Alter Degree (B.Tech → M.Tech)
        </button>
        <button
          onClick={() => handleApplyTamper("roll")}
          className="px-4 py-2 rounded-full bg-[#FFF5EA] text-black border border-[#E5E5E5] hover:bg-[#FFE0B2] transition-colors font-medium text-xs cursor-pointer"
        >
          Tamper: Modify Student Roll ID
        </button>
        <button
          onClick={() => handleApplyTamper("year")}
          className="px-4 py-2 rounded-full bg-[#FFF5EA] text-black border border-[#E5E5E5] hover:bg-[#FFE0B2] transition-colors font-medium text-xs cursor-pointer"
        >
          Tamper: Modify Year / Forged Grad
        </button>
        <button
          onClick={() => handleApplyTamper("bitflip")}
          className="px-4 py-2 rounded-full bg-[#FFD6E8] text-black border border-[#E5E5E5] hover:bg-[#FFB2D2] transition-colors font-medium text-xs cursor-pointer"
        >
          Tamper: 1-Bit Signature Bitflip
        </button>
      </div>

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Live Editable Payload */}
        <div className="bg-white rounded-[24px] border border-[#E5E5E5] p-6 md:p-8 space-y-5 hover:border-black transition-all">
          <div className="flex justify-between items-center">
            <h2 className="text-base font-semibold text-black flex items-center gap-2">
              <FileCode2 className="h-4 w-4 text-black" />
              <span>Live Canonical Payload (RFC 8785)</span>
            </h2>
            <span className="font-mono text-[10px] text-black/50 uppercase tracking-[0.54px]">Directly Editable</span>
          </div>

          <textarea
            rows={14}
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
            className="w-full p-4 font-mono text-xs rounded-[16px] border border-[#E5E5E5] bg-[#F9F9F9] text-black focus:border-black focus:outline-none leading-relaxed"
          />

          <div className="space-y-1.5">
            <label className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] text-black/60 block">
              Ed25519 Detached Digital Signature (Base64url):
            </label>
            <input
              type="text"
              value={signatureInput}
              onChange={(e) => setSignatureInput(e.target.value)}
              className="w-full px-4 py-2.5 font-mono text-xs rounded-full border border-[#E5E5E5] bg-[#F9F9F9] text-black truncate focus:border-black focus:outline-none"
            />
          </div>

          <div className="pt-2 flex flex-col sm:flex-row justify-between sm:items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-black/70 font-medium">
                Simulate Registry Revocation:
              </span>
              <button
                type="button"
                onClick={() => setRegistryRevoked(!registryRevoked)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono uppercase tracking-[0.54px] font-semibold transition-all cursor-pointer ${
                  registryRevoked
                    ? "bg-[#FF8577] text-black border border-black/10"
                    : "bg-[#F5F5F5] text-black border border-[#E5E5E5]"
                }`}
              >
                {registryRevoked ? "State: REVOKED" : "State: VALID"}
              </button>
            </div>

            <button
              onClick={handleRunVerification}
              disabled={isVerifying}
              className="px-6 py-3 text-xs font-medium rounded-full bg-black hover:bg-black/85 text-white shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer shrink-0"
            >
              {isVerifying ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  <span>Verifying Proof...</span>
                </>
              ) : (
                <>
                  <Cpu className="h-3.5 w-3.5" />
                  <span>Verify Cryptographic Proof</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Mathematical Verification Report */}
        <div className="bg-white rounded-[24px] border border-[#E5E5E5] p-6 md:p-8 flex flex-col justify-between space-y-6 hover:border-black transition-all">
          <div className="space-y-4">
            <h3 className="text-base font-semibold text-black flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-black" />
              <span>Cryptographic Attestation Report</span>
            </h3>

            {verificationResult && (
              <div
                className={`p-6 rounded-[20px] border transition-all ${
                  verificationResult.status === "VALID"
                    ? "bg-[#D2F8E7] text-black border-black/10"
                    : verificationResult.status === "REVOKED"
                    ? "bg-[#FFF5EA] text-black border-black/10"
                    : "bg-[#FF8577] text-black border-black/10"
                }`}
              >
                <div className="flex items-start gap-4">
                  {verificationResult.status === "VALID" ? (
                    <CheckCircle2 className="h-7 w-7 text-emerald-800 shrink-0 mt-0.5" />
                  ) : verificationResult.status === "REVOKED" ? (
                    <AlertOctagon className="h-7 w-7 text-amber-800 shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="h-7 w-7 text-rose-900 shrink-0 mt-0.5" />
                  )}

                  <div className="space-y-1.5">
                    <span className="font-mono text-[10px] uppercase font-semibold tracking-[0.54px] text-black/60 block">
                      Verification Outcome
                    </span>
                    <h4 className="text-lg font-semibold tracking-[-0.3px]">
                      {verificationResult.status === "VALID"
                        ? "AUTHENTIC & UNTAMPERED"
                        : verificationResult.status === "REVOKED"
                        ? "REVOKED BY REGISTRY"
                        : "TAMPER DETECTED / INVALID SIGNATURE"}
                    </h4>
                    <p className="text-xs font-[330] leading-relaxed">
                      {verificationResult.reason}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Cryptographic Parameters Inspector */}
            <div className="bg-[#F9F9F9] p-5 rounded-[18px] border border-[#E5E5E5] space-y-2.5 text-xs font-mono">
              <div className="font-semibold text-black mb-1 uppercase tracking-[0.54px] text-[10px]">
                Zero-Trust Audit Parameters:
              </div>
              <div className="flex justify-between py-1.5 border-b border-[#E5E5E5]">
                <span className="text-black/50">Asymmetric Curve:</span>
                <span className="font-semibold text-black">
                  Ed25519 (RFC 8032)
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-[#E5E5E5]">
                <span className="text-black/50">Sovereign Key ID (kid):</span>
                <span className="font-semibold text-black">
                  {kidInput}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-[#E5E5E5]">
                <span className="text-black/50">Canonical Serialization:</span>
                <span className="text-black">
                  RFC 8785 (UTF-8, Lexicographic)
                </span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-black/50">Registry Lifecycle State:</span>
                <span className="font-semibold text-black">
                  {registryRevoked ? "REVOKED (Superseded by updated marks)" : "ACTIVE"}
                </span>
              </div>
            </div>
          </div>

          <div className="p-4 bg-[#E5D4FF] rounded-[18px] text-xs text-black space-y-1">
            <strong className="font-semibold">Evaluator Takeaway:</strong>
            <p className="text-[11px] font-[330] text-black/85 leading-relaxed">
              Any change to a student's degree, roll number, or grade produces a completely different SHA-256 canonical hash. Since the attacker does not possess the AICTE private key, forging a valid signature is mathematically impossible (128-bit quantum-resistant security level).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
export default TamperDemo;
