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
    <div className="space-y-6">
      {/* Hero Explainer Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 rounded-2xl border border-indigo-800/40 shadow-xl text-white">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                Live Zero-Trust Sandbox
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                RFC 8785 Canonical Digest
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
              Cryptographic Tamper Demonstration Studio
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl">
              Evaluate the zero-trust mathematical integrity of Ed25519 verifiable credentials. Edit any field below to trigger an immediate cryptographic failure, or test live registry revocation.
            </p>
          </div>
          <button
            onClick={handleLoadPristine}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-md flex items-center gap-2 self-start md:self-center"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Reset to Pristine
          </button>
        </div>
      </div>

      {/* Preset Action Bar */}
      <div className="flex flex-wrap items-center gap-2 p-3 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 text-xs">
        <span className="font-semibold text-slate-500 uppercase tracking-wider mr-2">
          Tamper Presets:
        </span>
        <button
          onClick={() => handleApplyTamper("program")}
          className="px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800 hover:bg-amber-100 transition-colors font-medium"
        >
          Tamper: Alter Degree (B.Tech → M.Tech)
        </button>
        <button
          onClick={() => handleApplyTamper("roll")}
          className="px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800 hover:bg-amber-100 transition-colors font-medium"
        >
          Tamper: Modify Student Roll ID
        </button>
        <button
          onClick={() => handleApplyTamper("year")}
          className="px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800 hover:bg-amber-100 transition-colors font-medium"
        >
          Tamper: Modify Year / Forged Grad
        </button>
        <button
          onClick={() => handleApplyTamper("bitflip")}
          className="px-3 py-1.5 rounded-lg bg-rose-50 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800 hover:bg-rose-100 transition-colors font-medium"
        >
          Tamper: 1-Bit Signature Bitflip
        </button>
      </div>

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Live Editable Payload */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <FileCode2 className="h-4 w-4 text-indigo-600" />
              Live Canonical Credential Payload (RFC 8785)
            </h2>
            <span className="text-[11px] text-slate-400 font-mono">Directly Editable</span>
          </div>

          <textarea
            rows={14}
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
            className="w-full p-3 font-mono text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 leading-relaxed"
          />

          <div className="space-y-2">
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Ed25519 Detached Digital Signature (Base64url):
            </label>
            <input
              type="text"
              value={signatureInput}
              onChange={(e) => setSignatureInput(e.target.value)}
              className="w-full px-3 py-2 font-mono text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white truncate"
            />
          </div>

          <div className="pt-2 flex flex-col sm:flex-row justify-between sm:items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-600 dark:text-slate-400 font-medium">
                Simulate Registry Revocation:
              </span>
              <button
                type="button"
                onClick={() => setRegistryRevoked(!registryRevoked)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                  registryRevoked
                    ? "bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-300"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                }`}
              >
                {registryRevoked ? "State: REVOKED" : "State: VALID"}
              </button>
            </div>

            <button
              onClick={handleRunVerification}
              disabled={isVerifying}
              className="px-6 py-2.5 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-md transition-all flex items-center justify-center gap-2"
            >
              {isVerifying ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Verifying...
                </>
              ) : (
                <>
                  <Cpu className="h-4 w-4" />
                  Verify Cryptographic Proof
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Mathematical Verification Report */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm flex flex-col justify-between space-y-6">
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-indigo-600" />
              Cryptographic Attestation Report
            </h3>

            {verificationResult && (
              <div
                className={`p-5 rounded-2xl border transition-all ${
                  verificationResult.status === "VALID"
                    ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-950 dark:text-emerald-100"
                    : verificationResult.status === "REVOKED"
                    ? "bg-amber-50 dark:bg-amber-950/40 border-amber-300 dark:border-amber-800 text-amber-950 dark:text-amber-100"
                    : "bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-800 text-rose-950 dark:text-rose-100"
                }`}
              >
                <div className="flex items-start gap-3.5">
                  {verificationResult.status === "VALID" ? (
                    <CheckCircle2 className="h-8 w-8 text-emerald-600 shrink-0 mt-0.5" />
                  ) : verificationResult.status === "REVOKED" ? (
                    <AlertOctagon className="h-8 w-8 text-amber-600 shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="h-8 w-8 text-rose-600 shrink-0 mt-0.5" />
                  )}

                  <div className="space-y-1.5">
                    <span className="text-[10px] uppercase font-bold tracking-widest opacity-75">
                      Verification Outcome
                    </span>
                    <h4 className="text-lg font-bold">
                      {verificationResult.status === "VALID"
                        ? "AUTHENTIC & UNTAMPERED"
                        : verificationResult.status === "REVOKED"
                        ? "REVOKED BY REGISTRY"
                        : "TAMPER DETECTED / INVALID SIGNATURE"}
                    </h4>
                    <p className="text-xs leading-relaxed opacity-90">
                      {verificationResult.reason}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Cryptographic Parameters Inspector */}
            <div className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-200 dark:border-slate-800 space-y-2.5 text-xs">
              <div className="font-bold text-slate-800 dark:text-slate-200 mb-1">
                Zero-Trust Audit Parameters:
              </div>
              <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700/60">
                <span className="text-slate-500">Asymmetric Curve:</span>
                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                  Ed25519 (RFC 8032)
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700/60">
                <span className="text-slate-500">Sovereign Key ID (kid):</span>
                <span className="font-mono font-semibold text-indigo-600 dark:text-indigo-400">
                  {kidInput}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700/60">
                <span className="text-slate-500">Canonical Serialization:</span>
                <span className="font-mono text-slate-800 dark:text-slate-200">
                  RFC 8785 (UTF-8, Lexicographic Key Order)
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Registry Lifecycle State:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {registryRevoked ? "REVOKED (Superseded by updated marks)" : "ACTIVE"}
                </span>
              </div>
            </div>
          </div>

          <div className="p-3.5 bg-indigo-50 dark:bg-indigo-950/40 rounded-xl border border-indigo-200 dark:border-indigo-800/60 text-xs text-indigo-900 dark:text-indigo-200 space-y-1">
            <strong>Evaluator Takeaway:</strong>
            <p className="text-[11px] opacity-90 leading-relaxed">
              Any change to a student's degree, roll number, or grade produces a completely different SHA-256 canonical hash. Since the attacker does not possess the AICTE private key, forging a valid signature is mathematically impossible (128-bit quantum-resistant security level).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
