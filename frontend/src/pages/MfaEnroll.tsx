import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, Copy, Check, Download, AlertTriangle, ArrowRight } from "lucide-react";
import { apiClient, ApiException } from "@/lib/api";

interface MfaEnrollData {
  secret: string;
  provisioning_uri: string;
  backup_codes: string[];
}

export const MfaEnroll: React.FC = () => {
  const navigate = useNavigate();
  const [enrollData, setEnrollData] = useState<MfaEnrollData | null>(null);
  const [confirmCode, setConfirmCode] = useState("");
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedCodes, setCopiedCodes] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    // Initiate enrollment on mount
    const fetchEnrollData = async () => {
      try {
        const res = await apiClient<MfaEnrollData>("/api/v1/auth/mfa/enroll", {
          method: "POST",
        });
        setEnrollData(res);
      } catch (err: any) {
        if (err instanceof ApiException) {
          setError(err.error.message);
        } else {
          setError("Failed to generate MFA credentials. Please ensure you are signed in.");
        }
      }
    };

    fetchEnrollData();
  }, []);

  const handleCopySecret = () => {
    if (enrollData?.secret) {
      navigator.clipboard.writeText(enrollData.secret);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    }
  };

  const handleCopyBackupCodes = () => {
    if (enrollData?.backup_codes) {
      navigator.clipboard.writeText(enrollData.backup_codes.join("\n"));
      setCopiedCodes(true);
      setTimeout(() => setCopiedCodes(false), 2000);
    }
  };

  const handleDownloadBackupCodes = () => {
    if (!enrollData?.backup_codes) return;
    const blob = new Blob(
      [
        "AICTE APAAR-Sutra Backup Codes\n" +
          "Generated on: " +
          new Date().toISOString() +
          "\n\nEach code can only be used once:\n\n" +
          enrollData.backup_codes.map((c, i) => `${i + 1}. ${c}`).join("\n") +
          "\n\nKeep these codes in a safe, offline place.",
      ],
      { type: "text/plain;charset=utf-8" }
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "aicte-backup-codes.txt";
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await apiClient<{ status: string }>("/api/v1/auth/mfa/confirm", {
        method: "POST",
        body: JSON.stringify({ code: confirmCode.trim() }),
      });
      setIsSuccess(true);
      setTimeout(() => {
        navigate("/");
      }, 1500);
    } catch (err: any) {
      if (err instanceof ApiException) {
        setError(err.error.message);
      } else {
        setError("Invalid code. Please ensure your device clock is synced.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 flex justify-center items-center">
      <div className="max-w-2xl w-full bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="bg-slate-900 px-8 py-6 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600 rounded-lg">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Enrol in Two-Factor Authentication</h1>
              <p className="text-xs text-slate-400">Required for Privileged AICTE and Institutional Portals</p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-8 space-y-6">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
              {error}
            </div>
          )}

          {isSuccess ? (
            <div className="p-8 text-center space-y-3">
              <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
                <Check className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">MFA Activated Successfully!</h2>
              <p className="text-sm text-slate-500">Redirecting to your dashboard...</p>
            </div>
          ) : enrollData ? (
            <>
              {/* Step 1: Scan / Enter Secret */}
              <div className="space-y-3">
                <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs flex items-center justify-center font-bold">1</span>
                  Configure Authenticator App
                </h2>
                <p className="text-xs text-slate-600">
                  Open Google Authenticator, Microsoft Authenticator, or 1Password and enter the secret key below:
                </p>

                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between font-mono text-sm">
                  <span className="text-slate-800 font-semibold tracking-wider select-all">{enrollData.secret}</span>
                  <button
                    type="button"
                    onClick={handleCopySecret}
                    className="p-1.5 hover:bg-slate-200 rounded text-slate-600 transition-colors flex items-center gap-1 text-xs"
                  >
                    {copiedSecret ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                    <span>{copiedSecret ? "Copied" : "Copy"}</span>
                  </button>
                </div>
              </div>

              {/* Step 2: Backup Codes */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs flex items-center justify-center font-bold">2</span>
                    Single-Use Backup Codes
                  </h2>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={handleCopyBackupCodes}
                      className="px-2.5 py-1 text-xs border border-slate-300 rounded hover:bg-slate-50 text-slate-700 flex items-center gap-1"
                    >
                      {copiedCodes ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedCodes ? "Copied" : "Copy All"}</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleDownloadBackupCodes}
                      className="px-2.5 py-1 text-xs border border-slate-300 rounded hover:bg-slate-50 text-slate-700 flex items-center gap-1"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download .txt</span>
                    </button>
                  </div>
                </div>

                <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2 text-xs text-amber-800">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />
                  <span>Save these backup codes. If you lose your phone, each code can be used once to access your account.</span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 bg-slate-50 p-3 rounded-lg border border-slate-200 font-mono text-xs text-slate-700 text-center">
                  {enrollData.backup_codes.map((code) => (
                    <div key={code} className="p-1.5 bg-white border border-slate-200 rounded">
                      {code}
                    </div>
                  ))}
                </div>
              </div>

              {/* Step 3: Confirmation */}
              <form onSubmit={handleConfirm} className="space-y-3 pt-2 border-t border-slate-100">
                <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs flex items-center justify-center font-bold">3</span>
                  Confirm Activation
                </h2>
                <p className="text-xs text-slate-600">
                  Enter the 6-digit code currently shown in your authenticator app to confirm setup:
                </p>

                <div className="flex gap-3">
                  <input
                    type="text"
                    required
                    maxLength={6}
                    value={confirmCode}
                    onChange={(e) => setConfirmCode(e.target.value)}
                    placeholder="123456"
                    className="w-48 text-center font-mono tracking-widest text-lg py-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <button
                    type="submit"
                    disabled={isLoading || confirmCode.length !== 6}
                    className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-medium rounded-lg text-sm shadow transition-colors flex items-center gap-2 cursor-pointer"
                  >
                    {isLoading ? "Activating..." : "Activate Two-Factor"}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </form>
            </>
          ) : (
            <div className="py-12 text-center text-slate-500">Generating cryptographic MFA keys...</div>
          )}
        </div>
      </div>
    </div>
  );
};
