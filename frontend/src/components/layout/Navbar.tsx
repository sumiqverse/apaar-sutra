import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ShieldCheck, Sparkles, ExternalLink } from "lucide-react";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

export const Navbar: React.FC = () => {
  const { t } = useTranslation();
  const location = useLocation();

  const navLinks = [
    { to: "/", label: "AICTE Overview" },
    { to: "/institution-dashboard", label: "Institutions" },
    { to: "/reports", label: "Statutory Reports" },
    { to: "/verifier", label: "Verifier Hub" },
    { to: "/student/consent", label: "Student DPDP" },
    { to: "/demo-guide", label: "Demo Guide" },
  ];

  return (
    <div className="sticky top-0 z-40 bg-white">
      {/* 56px Editor-Clean Top Nav */}
      <header className="h-14 w-full border-b border-[#E5E5E5] px-6 flex items-center justify-between bg-white">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2.5 text-black hover:opacity-85 transition-opacity">
            <div className="w-7 h-7 bg-black text-white rounded-md flex items-center justify-center font-bold text-xs tracking-wider">
              AS
            </div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base tracking-tight text-black">
                APAAR-Sutra
              </span>
              <span className="font-mono text-[10px] uppercase font-semibold tracking-[0.54px] bg-[#F5F5F5] text-black px-1.5 py-0.5 rounded-sm border border-[#E5E5E5]">
                AICTE 2026
              </span>
            </div>
          </Link>

          {/* Nav links */}
          <nav className="hidden lg:flex items-center gap-1">
            {navLinks.map((item) => {
              const active = location.pathname === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`text-[13px] px-3 py-1.5 rounded-full transition-all ${
                    active
                      ? "text-black font-semibold bg-[#F5F5F5]"
                      : "text-neutral-600 hover:text-black hover:bg-neutral-50 font-normal"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Action Pills */}
        <div className="flex items-center gap-2.5">
          <LanguageSwitcher />

          <Link
            to="/developers"
            className="hidden sm:inline-flex items-center gap-1 text-[13px] font-medium text-neutral-600 hover:text-black px-2.5 py-1"
          >
            <span>API Specs</span>
            <ExternalLink className="w-3 h-3 text-neutral-400" />
          </Link>

          <Link
            to="/login"
            className="figma-pill-secondary text-[13px] !py-1.5 !px-4"
          >
            Switch Role
          </Link>

          <Link
            to="/demo-guide"
            className="figma-pill-primary text-[13px] !py-1.5 !px-4 shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5 text-white" />
            <span>Interactive Demo</span>
          </Link>
        </div>
      </header>

      {/* 36px Black Marquee Strip */}
      <div className="h-9 bg-black text-white flex items-center overflow-hidden border-b border-black select-none">
        <div className="animate-marquee flex items-center gap-8 whitespace-nowrap text-[11px] font-mono uppercase tracking-[0.6px] font-medium text-neutral-300">
          <span>• AICTE NATIONAL ACADEMIC REGISTRY & VERIFICATION ENGINE</span>
          <span className="text-[#D4FF5B]">• 25,053 SYNTHETIC ENROLMENTS ACTIVE</span>
          <span>• 60 ACCREDITED INSTITUTIONS</span>
          <span className="text-[#D2F8E7]">• 100% VERHOEFF CHECKSUM VERIFIED</span>
          <span>• ED25519 CRYPTOGRAPHIC SIGNATURES</span>
          <span className="text-[#E5D4FF]">• DPDP 2023 ZERO-TRUST PRIVACY COMPLIANT</span>
          <span>• DETERMINISTIC REPRODUCIBLE SEED 42</span>
          <span className="text-[#FF8577]">• CROSS-INSTITUTION CONCURRENT DUPLICATE DETECTION</span>

          {/* Repeated for seamless infinite scroll */}
          <span>• AICTE NATIONAL ACADEMIC REGISTRY & VERIFICATION ENGINE</span>
          <span className="text-[#D4FF5B]">• 25,053 SYNTHETIC ENROLMENTS ACTIVE</span>
          <span>• 60 ACCREDITED INSTITUTIONS</span>
          <span className="text-[#D2F8E7]">• 100% VERHOEFF CHECKSUM VERIFIED</span>
          <span>• ED25519 CRYPTOGRAPHIC SIGNATURES</span>
          <span className="text-[#E5D4FF]">• DPDP 2023 ZERO-TRUST PRIVACY COMPLIANT</span>
          <span>• DETERMINISTIC REPRODUCIBLE SEED 42</span>
          <span className="text-[#FF8577]">• CROSS-INSTITUTION CONCURRENT DUPLICATE DETECTION</span>
        </div>
      </div>
    </div>
  );
};
