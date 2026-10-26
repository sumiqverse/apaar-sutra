import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { ShieldCheck, Lock, Mail, KeyRound, AlertCircle, ArrowRight } from "lucide-react";
import { apiClient, setAuthTokens, ApiException } from "@/lib/api";

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as any)?.from?.pathname || "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep] = useState<"credentials" | "mfa">("credentials");
  const [tempToken, setTempToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");
  const [useBackupCode, setUseBackupCode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const res = await apiClient<{
        access_token?: string;
        refresh_token?: string;
        mfa_required?: boolean;
        mfa_setup_required?: boolean;
        temp_token?: string;
      }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      if (res.mfa_required && res.temp_token) {
        setTempToken(res.temp_token);
        setStep("mfa");
      } else if (res.mfa_setup_required && res.temp_token) {
        setTempToken(res.temp_token);
        navigate("/mfa-enroll", { state: { tempToken: res.temp_token } });
      } else if (res.access_token) {
        setAuthTokens(res.access_token, res.refresh_token);
        navigate(from, { replace: true });
      }
    } catch (err: any) {
      if (err instanceof ApiException) {
        setError(err.error.message);
      } else {
        setError("Unable to authenticate. Please check your credentials.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tempToken) return;

    setError(null);
    setIsLoading(true);

    try {
      const res = await apiClient<{
        access_token: string;
        refresh_token: string;
      }>("/api/v1/auth/mfa/verify", {
        method: "POST",
        body: JSON.stringify({
          temp_token: tempToken,
          code: mfaCode.trim(),
        }),
      });

      setAuthTokens(res.access_token, res.refresh_token);
      navigate(from, { replace: true });
    } catch (err: any) {
      if (err instanceof ApiException) {
        setError(err.error.message);
      } else {
        setError("Invalid verification code. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl border border-slate-100 overflow-hidden">
        {/* Header Header */}
        <div className="bg-slate-900 px-8 pt-8 pb-6 text-center text-white relative">
          <div className="mx-auto w-14 h-14 bg-indigo-600/30 border border-indigo-400/40 rounded-xl flex items-center justify-center mb-3 text-indigo-400 shadow-inner">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">APAAR-Sutra</h1>
          <p className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-semibold">
            AICTE National Student Registry & Verification Hub
          </p>
        </div>

        {/* Content Body */}
        <div className="p-8">
          {error && (
            <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 text-sm text-red-800">
              <AlertCircle className="w-5 h-5 shrink-0 text-red-600 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {step === "credentials" ? (
            <form onSubmit={handleCredentialsSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Official Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="officer@aicte.gov.in"
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-2 py-3 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-medium rounded-lg text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                {isLoading ? (
                  <span>Authenticating...</span>
                ) : (
                  <>
                    <span>Sign In to Platform</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handleMfaSubmit} className="space-y-5">
              <div className="text-center pb-2">
                <KeyRound className="w-10 h-10 text-indigo-600 mx-auto mb-2" />
                <h3 className="text-base font-semibold text-slate-900">Multi-Factor Authentication</h3>
                <p className="text-xs text-slate-500 mt-1">
                  {useBackupCode
                    ? "Enter an unused 9-character backup code"
                    : "Enter the 6-digit TOTP code generated by your Authenticator app"}
                </p>
              </div>

              <div>
                <input
                  type="text"
                  required
                  autoFocus
                  maxLength={useBackupCode ? 10 : 6}
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  placeholder={useBackupCode ? "A1B2-C3D4" : "000000"}
                  className="w-full text-center tracking-widest text-xl font-mono py-3 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 uppercase"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-medium rounded-lg text-sm shadow-md transition-all flex items-center justify-center gap-2"
              >
                {isLoading ? "Verifying..." : "Verify & Complete Login"}
              </button>

              <div className="text-center pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setUseBackupCode(!useBackupCode);
                    setMfaCode("");
                    setError(null);
                  }}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  {useBackupCode ? "Use Authenticator app code instead" : "Lost access? Use a backup code"}
                </button>
              </div>
            </form>
          )}

          <div className="mt-8 pt-4 border-t border-slate-100 text-center">
            <span className="text-[11px] text-slate-400">
              Protected by Argon2id, RFC 6238 TOTP & Rate Limiting
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
