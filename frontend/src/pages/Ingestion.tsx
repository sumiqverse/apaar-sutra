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
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Student Data Ingestion Portal</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
              Phase 3 Ingestion Engine
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Standardized onboarding of student academic cohorts with real-time APAAR verification, cryptographic encryption, and AICTE compliance.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-slate-100 p-1 rounded-2xl border border-slate-200 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all whitespace-nowrap cursor-pointer ${
                  isActive
                    ? "bg-white text-indigo-700 shadow-sm border border-slate-200/60"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-indigo-600" : "text-slate-500"}`} />
                <span>{tab.label}</span>
                {tab.badge && (
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                      isActive ? "bg-indigo-50 text-indigo-600" : "bg-slate-200 text-slate-600"
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
