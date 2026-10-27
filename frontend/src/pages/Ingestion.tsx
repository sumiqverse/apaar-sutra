import React, { useState } from "react";
import {
  UploadCloud,
  UserPlus,
  History,
  Building,
} from "lucide-react";
import { UploadWizard } from "../components/ingestion/UploadWizard";
import { StudentEnrolForm } from "../components/ingestion/StudentEnrolForm";
import { BatchHistory } from "../components/ingestion/BatchHistory";
import { ProgramIntakeView } from "../components/ingestion/ProgramIntakeView";

export const Ingestion: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"bulk" | "single" | "history" | "intake">("bulk");

  const tabs = [
    {
      id: "bulk",
      label: "Bulk Ingestion Wizard",
      icon: UploadCloud,
      badge: "CSV / XLSX (50k)",
    },
    {
      id: "single",
      label: "Single Registration",
      icon: UserPlus,
      badge: "21 Fields",
    },
    {
      id: "history",
      label: "Batch Ledger",
      icon: History,
      badge: null,
    },
    {
      id: "intake",
      label: "Program Quotas",
      icon: Building,
      badge: "15% Cap",
    },
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto" role="region" aria-label="Student Data Ingestion Portal">
      {/* Top Banner (Cream Color-Block) */}
      <div className="bg-[#FFF5EA] text-black rounded-[24px] p-8 md:p-10 flex flex-col md:flex-row items-start md:items-end justify-between gap-6">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-black text-white font-semibold uppercase tracking-[0.54px]">
              AICTE Batch Engine
            </span>
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-white text-black border border-black/10 font-semibold uppercase tracking-[0.54px]">
              50k Bulk Pipeline
            </span>
          </div>
          <h1 className="text-3xl md:text-5xl font-medium tracking-[-1.2px] text-black leading-[1.05]">
            Student Data Ingestion Portal
          </h1>
          <p className="text-sm md:text-base font-[330] text-black/80 max-w-2xl tracking-[-0.26px]">
            Standardized onboarding of student academic cohorts with real-time APAAR verification, cryptographic encryption, and AICTE compliance.
          </p>
        </div>

        {/* Tab Switcher (Pill Toggles) */}
        <div className="flex items-center bg-white p-1.5 rounded-full border border-black/10 overflow-x-auto shrink-0 max-w-full">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium transition-all whitespace-nowrap cursor-pointer ${
                  isActive
                    ? "bg-black text-white shadow-sm"
                    : "text-black/70 hover:text-black hover:bg-black/5"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? "text-white" : "text-black/60"}`} />
                <span>{tab.label}</span>
                {tab.badge && (
                  <span
                    className={`text-[9px] px-2 py-0.5 rounded-full font-mono uppercase tracking-[0.54px] font-semibold ${
                      isActive ? "bg-white/20 text-white" : "bg-[#F5F5F5] text-black/70"
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main View Area */}
      <div className="pt-2">
        {activeTab === "bulk" && <UploadWizard />}
        {activeTab === "single" && <StudentEnrolForm />}
        {activeTab === "history" && <BatchHistory />}
        {activeTab === "intake" && <ProgramIntakeView />}
      </div>
    </div>
  );
};

export default Ingestion;
