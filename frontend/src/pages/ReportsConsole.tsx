import React, { useEffect, useState } from "react";
import {
  FileText,
  Download,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Search,
  Calendar,
  Layers,
  TrendingUp,
  Award,
  Users,
  Copy,
  Check,
  ExternalLink,
  Filter,
} from "lucide-react";
import { apiClient } from "@/lib/api";

interface ReportCatalogItem {
  type: string;
  title: string;
  description: string;
  category: string;
  default_format: string;
  supported_formats: string[];
}

interface GeneratedReportItem {
  id: string;
  report_type: string;
  title: string;
  format: string;
  verification_hash: string;
  row_count: number;
  filters: Record<string, any>;
  status: string;
  created_at: string;
}

interface VerificationResult {
  verified: boolean;
  message: string;
  report?: {
    id: string;
    title: string;
    report_type: string;
    institution_id: string | null;
    row_count: number;
    filters: Record<string, any>;
    created_at: string;
  };
  hash_checked: string;
}

export const ReportsConsole: React.FC = () => {
  const [catalog, setCatalog] = useState<ReportCatalogItem[]>([]);
  const [history, setHistory] = useState<GeneratedReportItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [generatingType, setGeneratingType] = useState<string | null>(null);

  // Filter state for generation
  const [academicYear, setAcademicYear] = useState<string>("2025-26");
  const [selectedFormats, setSelectedFormats] = useState<Record<string, string>>({});

  // Hash verification state
  const [verifyHashInput, setVerifyHashInput] = useState<string>("");
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verifyResult, setVerifyResult] = useState<VerificationResult | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [historySearch, setHistorySearch] = useState<string>("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [catRes, histRes] = await Promise.all([
        apiClient<ReportCatalogItem[]>("/api/v1/reports/catalog"),
        apiClient<GeneratedReportItem[]>("/api/v1/reports/history"),
      ]);
      setCatalog(catRes);
      setHistory(histRes);

      // Default format map
      const fMap: Record<string, string> = {};
      catRes.forEach((item) => {
        fMap[item.type] = item.default_format || "PDF";
      });
      setSelectedFormats(fMap);
    } catch (err) {
      console.error("Failed to load reports catalog or history:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (type: string) => {
    setGeneratingType(type);
    try {
      const format = selectedFormats[type] || "PDF";
      const payload = {
        report_type: type,
        format: format,
        academic_year: academicYear,
        filters: { academic_year: academicYear },
      };

      const result = await apiClient<GeneratedReportItem>("/api/v1/reports/generate", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      // Refresh history list
      setHistory((prev) => [result, ...prev]);

      // Trigger instant download
      handleDownload(result.id, result.title, result.format);
    } catch (err: any) {
      alert("Report generation failed: " + (err.message || "Unknown error"));
    } finally {
      setGeneratingType(null);
    }
  };

  const handleDownload = (id: string, title: string, format: string) => {
    const token = localStorage.getItem("apaar_access_token");
    const downloadUrl = `/api/v1/reports/download/${id}`;

    fetch(downloadUrl, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => {
        if (!res.ok) throw new Error("Download failed");
        return res.blob();
      })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const ext = format.toLowerCase();
        a.download = `${title.replace(/[\s/]/g, "_")}_${new Date().toISOString().slice(0, 10)}.${ext}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      })
      .catch((err) => {
        alert("Failed to download report: " + err.message);
      });
  };

  const handleVerifyHash = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!verifyHashInput.trim()) return;

    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await apiClient<VerificationResult>(
        `/api/v1/reports/verify?hash=${encodeURIComponent(verifyHashInput.trim())}`
      );
      setVerifyResult(res);
    } catch (err: any) {
      setVerifyResult({
        verified: false,
        message: err.message || "Verification request failed",
        hash_checked: verifyHashInput.trim(),
      });
    } finally {
      setVerifying(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2500);
  };

  const getReportIcon = (type: string) => {
    switch (type) {
      case "state_wise_intake":
        return <Layers className="w-5 h-5 text-indigo-500" />;
      case "overshoot_institutions":
        return <AlertTriangle className="w-5 h-5 text-rose-500" />;
      case "supernumerary_distribution":
        return <Users className="w-5 h-5 text-purple-500" />;
      case "duplicate_register":
        return <ShieldCheck className="w-5 h-5 text-amber-500" />;
      case "institution_risk_ranking":
        return <TrendingUp className="w-5 h-5 text-orange-500" />;
      case "data_completeness":
        return <CheckCircle className="w-5 h-5 text-emerald-500" />;
      case "accreditation_support":
        return <Award className="w-5 h-5 text-cyan-500" />;
      default:
        return <FileText className="w-5 h-5 text-blue-500" />;
    }
  };

  const filteredHistory = history.filter((item) => {
    const q = historySearch.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      item.report_type.toLowerCase().includes(q) ||
      item.verification_hash.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600/10 text-indigo-600 dark:text-indigo-400 rounded-xl">
              <FileText className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                Statutory Reports & Regulatory Engine
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                AICTE compliant reports in PDF, XLSX, and CSV with tamper-proof SHA-256 cryptographic provenance.
              </p>
            </div>
          </div>
        </div>

        {/* Global Controls */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm">
            <Calendar className="w-4 h-4 text-slate-400" />
            <span className="text-slate-600 dark:text-slate-300 font-medium">Session:</span>
            <select
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="bg-transparent font-semibold text-indigo-600 dark:text-indigo-400 focus:outline-none cursor-pointer"
            >
              <option value="2025-26">2025-26 (Current)</option>
              <option value="2024-25">2024-25</option>
              <option value="2023-24">2023-24</option>
            </select>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Cryptographic Hash Verification Widget */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-2xl p-6 shadow-xl border border-indigo-500/20">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold tracking-wider uppercase mb-1">
            <ShieldCheck className="w-4 h-4" />
            Public Verification Endpoint (/reports/verify?hash=)
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">
            Verify Statutory Report Authenticity
          </h2>
          <p className="text-sm text-slate-300 mb-4">
            Every statutory export contains an embedded SHA-256 integrity hash calculated over the exact records and parameters. Enter any report hash to verify its official regulatory origin.
          </p>

          <form onSubmit={handleVerifyHash} className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Enter 64-character SHA-256 report verification hash..."
                value={verifyHashInput}
                onChange={(e) => setVerifyHashInput(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white placeholder-slate-400 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
            <button
              type="submit"
              disabled={verifying || !verifyHashInput.trim()}
              className="px-5 py-2.5 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm font-semibold rounded-xl transition flex items-center justify-center gap-2 shrink-0 shadow-lg shadow-indigo-500/30"
            >
              {verifying ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
              Verify Ledger
            </button>
          </form>

          {verifyResult && (
            <div className={`mt-4 p-4 rounded-xl border text-sm transition-all ${
              verifyResult.verified
                ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-200"
                : "bg-rose-950/60 border-rose-500/40 text-rose-200"
            }`}>
              <div className="flex items-start gap-3">
                {verifyResult.verified ? (
                  <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                )}
                <div className="space-y-1">
                  <div className="font-semibold text-white">
                    {verifyResult.verified ? "Official Report Verified Authentic" : "Verification Failed"}
                  </div>
                  <div className="text-xs opacity-90">{verifyResult.message}</div>
                  {verifyResult.report && (
                    <div className="mt-2 text-xs grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-white/10">
                      <div>
                        <span className="opacity-70">Title:</span>{" "}
                        <span className="font-medium text-white">{verifyResult.report.title}</span>
                      </div>
                      <div>
                        <span className="opacity-70">Rows:</span>{" "}
                        <span className="font-medium text-white">{verifyResult.report.row_count}</span>
                      </div>
                      <div>
                        <span className="opacity-70">Generated:</span>{" "}
                        <span className="font-medium text-white">
                          {new Date(verifyResult.report.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div>
                        <span className="opacity-70">Status:</span>{" "}
                        <span className="font-medium text-emerald-400">AUTHENTIC</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 8 Statutory Reports Catalog */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Statutory Compliance Catalog
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Select desired export format (PDF with server-side charts, XLSX workbook, or raw CSV).
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 rounded-full border border-indigo-200 dark:border-indigo-800">
            {catalog.length} Statutory Modules
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {catalog.map((report) => {
            const isGenerating = generatingType === report.type;
            const currentFormat = selectedFormats[report.type] || "PDF";

            return (
              <div
                key={report.type}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-start justify-between mb-3">
                    <div className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 group-hover:scale-110 transition-transform">
                      {getReportIcon(report.type)}
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                      {report.category}
                    </span>
                  </div>

                  <h3 className="font-semibold text-slate-900 dark:text-white text-sm line-clamp-1 mb-1">
                    {report.title}
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-3 mb-4 leading-relaxed">
                    {report.description}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-3">
                  {/* Format Pills */}
                  <div className="flex items-center gap-1.5">
                    {report.supported_formats.map((fmt) => (
                      <button
                        key={fmt}
                        onClick={() =>
                          setSelectedFormats((prev) => ({ ...prev, [report.type]: fmt }))
                        }
                        className={`text-[11px] font-semibold px-2.5 py-1 rounded-md transition ${
                          currentFormat === fmt
                            ? "bg-indigo-600 text-white"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                        }`}
                      >
                        {fmt}
                      </button>
                    ))}
                  </div>

                  {/* Generate Button */}
                  <button
                    onClick={() => handleGenerate(report.type)}
                    disabled={isGenerating}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-slate-900 hover:bg-indigo-600 dark:bg-slate-800 dark:hover:bg-indigo-600 text-white text-xs font-semibold rounded-xl transition shadow-sm"
                  >
                    {isGenerating ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        Generating {currentFormat}...
                      </>
                    ) : (
                      <>
                        <Download className="w-3.5 h-3.5" />
                        Generate & Download
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Generated Reports Ledger & History */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              Generated Reports Ledger
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Audit log of compiled reports with cryptographic verification hashes and re-download capability.
            </p>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Search reports or hashes..."
              value={historySearch}
              onChange={(e) => setHistorySearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        {filteredHistory.length === 0 ? (
          <div className="text-center py-12 text-slate-400 text-sm">
            No generated reports found matching query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/60 uppercase font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4">Report Details</th>
                  <th className="py-3 px-4">Format</th>
                  <th className="py-3 px-4">Rows</th>
                  <th className="py-3 px-4">Integrity Hash (SHA-256)</th>
                  <th className="py-3 px-4">Generated At</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredHistory.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 font-medium text-slate-900 dark:text-white">
                      <div className="font-semibold text-xs">{item.title}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{item.report_type}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        item.format === "PDF"
                          ? "bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300"
                          : item.format === "XLSX"
                          ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300"
                          : "bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300"
                      }`}>
                        {item.format}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-medium">
                      {item.row_count.toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-500 dark:text-slate-400">
                          {item.verification_hash.slice(0, 10)}...{item.verification_hash.slice(-8)}
                        </span>
                        <button
                          onClick={() => copyToClipboard(item.verification_hash)}
                          title="Copy Full SHA256 Hash"
                          className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        >
                          {copiedHash === item.verification_hash ? (
                            <Check className="w-3.5 h-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleDownload(item.id, item.title, item.format)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-slate-100 hover:bg-indigo-50 dark:bg-slate-800 dark:hover:bg-indigo-950 text-slate-700 hover:text-indigo-600 dark:text-slate-300 dark:hover:text-indigo-400 rounded-lg text-xs font-semibold transition"
                      >
                        <Download className="w-3.5 h-3.5" />
                        Re-download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
export default ReportsConsole;
