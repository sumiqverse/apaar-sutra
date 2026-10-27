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
    <div className="min-h-screen flex items-center justify-center bg-[#F9F9F9] p-4 md:p-8">
      <div className="max-w-md w-full bg-white rounded-[24px] border border-[#E5E5E5] overflow-hidden p-8 md:p-10 space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-full bg-black text-white flex items-center justify-center mx-auto mb-2">
            <ShieldCheck className="w-6 h-6 text-[#D4FF5B]" />
          </div>
          <h1 className="text-2xl md:text-3xl font-medium tracking-[-0.96px] text-black">
            APAAR-Sutra
          </h1>
          <p className="font-mono text-[10px] text-black/60 uppercase tracking-[0.54px] font-semibold">
            AICTE National Student Registry & Verification Hub
          </p>
        </div>

        {error && (
          <div className="p-3 bg-[#FFF5F5] border border-rose-200 rounded-[12px] flex items-start gap-2.5 text-xs text-rose-800">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {step === "credentials" ? (
          <form onSubmit={handleCredentialsSubmit} className="space-y-4">
            <div>
              <label className="block font-mono text-[10px] font-semibold uppercase tracking-[0.54px] text-black/60 mb-1.5">
                Official Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 absolute left-3.5 top-3.5 text-black/40" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="officer@aicte.gov.in"
                  className="w-full pl-10 pr-4 py-2.5 bg-white border border-[#E5E5E5] rounded-[12px] text-xs text-black placeholder-black/40 focus:outline-none focus:border-black transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block font-mono text-[10px] font-semibold uppercase tracking-[0.54px] text-black/60 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3.5 top-3.5 text-black/40" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-4 py-2.5 bg-white border border-[#E5E5E5] rounded-[12px] text-xs text-black placeholder-black/40 focus:outline-none focus:border-black transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-3 px-6 bg-black hover:bg-black/85 disabled:opacity-50 text-white font-medium rounded-full text-xs tracking-[-0.1px] transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              {isLoading ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <span>Sign In to Platform</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleMfaSubmit} className="space-y-4">
            <div className="text-center pb-1 space-y-1">
              <div className="w-10 h-10 rounded-full bg-[#F5F5F5] border border-[#E5E5E5] flex items-center justify-center mx-auto text-black">
                <KeyRound className="w-5 h-5 text-black" />
              </div>
              <h3 className="text-sm font-semibold text-black tracking-[-0.2px]">
                Multi-Factor Authentication
              </h3>
              <p className="text-xs font-[330] text-black/60">
                {useBackupCode
                  ? "Enter an unused 9-character backup code"
                  : "Enter the 6-digit TOTP code generated by your Authenticator app (or 000000 for demo)"}
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
                className="w-full text-center tracking-widest text-lg font-mono py-2.5 bg-white border border-[#E5E5E5] rounded-[12px] focus:outline-none focus:border-black uppercase text-black"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-6 bg-black hover:bg-black/85 disabled:opacity-50 text-white font-medium rounded-full text-xs tracking-[-0.1px] transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              {isLoading ? "Verifying..." : "Verify & Complete Login"}
            </button>

            <div className="text-center pt-1">
              <button
                type="button"
                onClick={() => {
                  setUseBackupCode(!useBackupCode);
                  setMfaCode("");
                  setError(null);
                }}
                className="text-xs text-black/60 hover:text-black transition-colors"
              >
                {useBackupCode ? "Use Authenticator app code instead" : "Lost access? Use a backup code"}
              </button>
            </div>
          </form>
        )}

        <div className="pt-4 border-t border-[#E5E5E5] flex flex-col items-center gap-3 text-center">
          <button
            type="button"
            onClick={() => navigate("/demo-guide")}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-medium bg-[#D4FF5B] text-black hover:bg-[#D4FF5B]/90 transition-all cursor-pointer"
          >
            <span>⚡ SIH Finals: 1-Click Role Switcher & Guide</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <span className="font-mono text-[10px] text-black/40 uppercase tracking-[0.54px]">
            Protected by Argon2id • RFC 6238 TOTP • Zero-Trust
          </span>
        </div>
      </div>
    </div>
  );
};
