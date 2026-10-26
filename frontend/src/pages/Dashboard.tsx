import React from "react";
import { useTranslation } from "react-i18next";
import { Users, CheckCircle2, AlertOctagon, TrendingUp, Building2 } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

const analyticsData = [
  { state: "Maharashtra", students: 14200, verified: 13800 },
  { state: "Tamil Nadu", students: 12100, verified: 11950 },
  { state: "Karnataka", students: 9800, verified: 9400 },
  { state: "Delhi", students: 8600, verified: 8350 },
  { state: "Uttar Pradesh", students: 16500, verified: 15400 },
  { state: "Gujarat", students: 7800, verified: 7600 },
];

export const Dashboard: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          {t("nav.dashboard")}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          AICTE National Directorate - Academic Credential Overview & Telemetry
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-brand-50 text-brand-600 rounded-lg">
            <Users className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Total Registered</p>
            <h3 className="text-xl font-bold text-slate-900">1,248,390</h3>
            <span className="text-[11px] text-emerald-600 font-medium">↑ 12.4% this semester</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Verified Credentials</p>
            <h3 className="text-xl font-bold text-slate-900">1,189,420</h3>
            <span className="text-[11px] text-slate-500">95.2% verification rate</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-rose-50 text-rose-600 rounded-lg">
            <AlertOctagon className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Flagged Anomalies</p>
            <h3 className="text-xl font-bold text-slate-900">142</h3>
            <span className="text-[11px] text-rose-600 font-medium">Cross-college duplicates</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg">
            <Building2 className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500">Active Colleges</p>
            <h3 className="text-xl font-bold text-slate-900">4,120</h3>
            <span className="text-[11px] text-indigo-600 font-medium">Pan-India technical institutes</span>
          </div>
        </div>
      </div>

      {/* State Analytics Chart */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold text-slate-900">State-wise Student Enrollment vs. Verification</h3>
            <p className="text-xs text-slate-500">Real-time aggregate data keyed by APAAR 12-digit records</p>
          </div>
          <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-medium">
            <TrendingUp className="h-3.5 w-3.5" /> High Ingestion Flow
          </span>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={analyticsData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="state" stroke="#64748b" fontSize={12} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: "#ffffff", borderRadius: "8px", border: "1px solid #e2e8f0" }}
              />
              <Bar dataKey="students" name="Enrolled" fill="#0284c7" radius={[4, 4, 0, 0]} />
              <Bar dataKey="verified" name="Verified" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
