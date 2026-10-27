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
    <div className="space-y-8 max-w-7xl mx-auto" role="region" aria-label="Statutory Reports Console">
      {/* Top Banner (Lilac Color-Block) */}
      <div className="bg-[#E5D4FF] text-black rounded-[24px] p-8 md:p-10 flex flex-col md:flex-row items-start md:items-end justify-between gap-6">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-black text-white font-semibold uppercase tracking-[0.54px]">
              AICTE Compliance
            </span>
            <span className="font-mono text-xs px-3 py-1 rounded-full bg-white text-black border border-black/10 font-semibold uppercase tracking-[0.54px]">
              Statutory Provenance
            </span>
          </div>
          <h1 className="text-3xl md:text-5xl font-medium tracking-[-1.2px] text-black leading-[1.05]">
            Statutory Reports & Regulatory Engine
          </h1>
          <p className="text-sm md:text-base font-[330] text-black/80 max-w-2xl tracking-[-0.26px]">
            AICTE compliant audit exports in PDF, XLSX, and CSV with tamper-proof SHA-256 cryptographic provenance.
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 shrink-0 flex-wrap">
          <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-black/10 text-xs">
            <Calendar className="w-3.5 h-3.5 text-black/60" />
            <span className="font-mono uppercase tracking-[0.54px] text-black/60 font-semibold">Session:</span>
            <select
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="bg-transparent font-semibold text-black focus:outline-none cursor-pointer"
            >
              <option value="2025-26">2025-26 (Current)</option>
              <option value="2024-25">2024-25</option>
              <option value="2023-24">2023-24</option>
            </select>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 text-xs font-medium text-black bg-white border border-black/10 rounded-full hover:bg-black/5 transition-all cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Cryptographic Hash Verification (Navy Color-Block Section) */}
      <section className="bg-[#0C1033] text-white rounded-[24px] p-8 md:p-12 space-y-6">
        <div className="max-w-3xl space-y-2">
          <div className="flex items-center gap-2 text-[#D4FF5B] font-mono text-xs uppercase tracking-[0.54px] font-semibold">
            <ShieldCheck className="w-4 h-4" />
            <span>Public Verification Endpoint (/reports/verify?hash=)</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-medium tracking-[-0.96px] text-white">
            Verify Statutory Report Authenticity
          </h2>
          <p className="text-sm font-[330] text-white/80 leading-relaxed">
            Every statutory export contains an embedded SHA-256 integrity hash calculated over the exact records and parameters. Enter any report hash to verify its official regulatory origin.
          </p>
        </div>

        <form onSubmit={handleVerifyHash} className="flex flex-col sm:flex-row gap-3 max-w-3xl">
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Enter 64-character SHA-256 report verification hash..."
              value={verifyHashInput}
              onChange={(e) => setVerifyHashInput(e.target.value)}
              className="w-full px-5 py-3 rounded-full bg-white/10 border border-white/20 text-white placeholder-white/40 font-mono text-xs focus:outline-none focus:border-white transition-all"
            />
          </div>
          <button
            type="submit"
            disabled={verifying || !verifyHashInput.trim()}
            className="px-6 py-3 bg-white hover:bg-white/90 disabled:opacity-50 text-black text-xs font-semibold rounded-full transition-all flex items-center justify-center gap-2 shrink-0 cursor-pointer"
          >
            {verifying ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5 text-black" />}
            <span>Verify Ledger</span>
          </button>
        </form>

        {verifyResult && (
          <div className={`p-5 rounded-[20px] border text-xs max-w-3xl transition-all ${
            verifyResult.verified
              ? "bg-[#D2F8E7] text-black border-black/10"
              : "bg-[#FF8577] text-black border-black/10"
          }`}>
            <div className="flex items-start gap-3">
              {verifyResult.verified ? (
                <CheckCircle className="w-5 h-5 text-emerald-800 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-rose-900 shrink-0 mt-0.5" />
              )}
              <div className="space-y-1.5 flex-1">
                <div className="font-semibold text-sm">
                  {verifyResult.verified ? "Official Report Verified Authentic" : "Verification Failed"}
                </div>
                <div className="font-[330]">{verifyResult.message}</div>
                {verifyResult.report && (
                  <div className="mt-3 text-xs grid grid-cols-2 sm:grid-cols-4 gap-2 pt-3 border-t border-black/10 font-mono">
                    <div>
                      <span className="text-black/60 block text-[10px]">TITLE</span>
                      <span className="font-semibold">{verifyResult.report.title}</span>
                    </div>
                    <div>
                      <span className="text-black/60 block text-[10px]">ROWS</span>
                      <span className="font-semibold">{verifyResult.report.row_count}</span>
                    </div>
                    <div>
                      <span className="text-black/60 block text-[10px]">GENERATED</span>
                      <span className="font-semibold">
                        {new Date(verifyResult.report.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div>
                      <span className="text-black/60 block text-[10px]">STATUS</span>
                      <span className="font-bold text-emerald-800">AUTHENTIC</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Statutory Reports Catalog (White Canvas with Hairline Cards) */}
      <section className="space-y-5">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <span className="font-mono text-xs uppercase tracking-[0.54px] font-semibold text-black/60">
              Audit & Compliance
            </span>
            <h2 className="text-xl md:text-2xl font-medium tracking-[-0.6px] text-black">
              Statutory Compliance Catalog
            </h2>
            <p className="text-xs font-[330] text-black/60">
              Select desired export format (PDF with server-side charts, XLSX workbook, or raw CSV).
            </p>
          </div>
          <span className="font-mono text-xs font-semibold px-3 py-1 bg-[#F5F5F5] text-black rounded-full border border-[#E5E5E5]">
            {catalog.length} MODULES
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {catalog.map((report) => {
            const isGenerating = generatingType === report.type;
            const currentFormat = selectedFormats[report.type] || "PDF";

            return (
              <div
                key={report.type}
                className="bg-white border border-[#E5E5E5] rounded-[20px] p-6 flex flex-col justify-between hover:border-black transition-all group"
              >
                <div>
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-9 h-9 rounded-full bg-[#F5F5F5] border border-[#E5E5E5] flex items-center justify-center text-black">
                      {getReportIcon(report.type)}
                    </div>
                    <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.54px] px-2.5 py-0.5 rounded-full bg-[#F5F5F5] text-black border border-[#E5E5E5]">
                      {report.category}
                    </span>
                  </div>

                  <h3 className="font-semibold text-black text-sm line-clamp-1 mb-1 tracking-[-0.2px]">
                    {report.title}
                  </h3>
                  <p className="text-xs font-[330] text-black/65 line-clamp-3 mb-4 leading-relaxed">
                    {report.description}
                  </p>
                </div>

                <div className="pt-4 border-t border-[#E5E5E5] space-y-3">
                  {/* Format Pills */}
                  <div className="flex items-center gap-1.5">
                    {report.supported_formats.map((fmt) => (
                      <button
                        key={fmt}
                        onClick={() =>
                          setSelectedFormats((prev) => ({ ...prev, [report.type]: fmt }))
                        }
                        className={`text-[11px] font-mono font-semibold px-3 py-1 rounded-full transition-all cursor-pointer ${
                          currentFormat === fmt
                            ? "bg-black text-white"
                            : "bg-[#F5F5F5] text-black border border-[#E5E5E5] hover:bg-[#EAEAEA]"
                        }`}
                      >
                        {fmt}
                      </button>
                    ))}
                  </div>

                  {/* Generate Button (Black Pill Primary) */}
                  <button
                    onClick={() => handleGenerate(report.type)}
                    disabled={isGenerating}
                    className="w-full flex items-center justify-center gap-2 py-2.5 bg-black hover:bg-black/85 disabled:opacity-50 text-white text-xs font-medium rounded-full transition-all cursor-pointer"
                  >
                    {isGenerating ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Generating {currentFormat}...</span>
                      </>
                    ) : (
                      <>
                        <Download className="w-3.5 h-3.5" />
                        <span>Generate & Download</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Generated Reports Ledger & History (White Canvas) */}
      <section className="bg-white border border-[#E5E5E5] rounded-[24px] p-6 md:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="font-mono text-xs uppercase tracking-[0.54px] font-semibold text-black/60">
              Audit & Provenance
            </span>
            <h2 className="text-xl font-medium tracking-[-0.5px] text-black">
              Generated Reports Ledger
            </h2>
            <p className="text-xs font-[330] text-black/60">
              Audit log of compiled reports with cryptographic verification hashes and re-download capability.
            </p>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-black/40" />
            <input
              type="text"
              placeholder="Search reports or hashes..."
              value={historySearch}
              onChange={(e) => setHistorySearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 text-xs rounded-full bg-white border border-[#E5E5E5] text-black placeholder-black/40 focus:outline-none focus:border-black font-mono"
            />
          </div>
        </div>

        {filteredHistory.length === 0 ? (
          <div className="text-center py-12 text-black/40 text-xs font-mono uppercase tracking-[0.54px]">
            No generated reports found matching query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F9F9F9] uppercase font-semibold font-mono text-[10px] tracking-[0.54px] text-black/60 border-b border-[#E5E5E5]">
                <tr>
                  <th className="py-3 px-4">Report Details</th>
                  <th className="py-3 px-4">Format</th>
                  <th className="py-3 px-4">Rows</th>
                  <th className="py-3 px-4">Integrity Hash (SHA-256)</th>
                  <th className="py-3 px-4">Generated At</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E5]">
                {filteredHistory.map((item) => (
                  <tr key={item.id} className="hover:bg-[#F9F9F9] transition-colors">
                    <td className="py-3.5 px-4 font-medium text-black">
                      <div className="font-semibold text-xs tracking-[-0.1px]">{item.title}</div>
                      <div className="text-[11px] text-black/50 font-mono">{item.report_type}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase tracking-[0.54px] ${
                        item.format === "PDF"
                          ? "bg-[#FFD6E8] text-black"
                          : item.format === "XLSX"
                          ? "bg-[#D2F8E7] text-black"
                          : "bg-[#FFF5EA] text-black border border-[#E5E5E5]"
                      }`}>
                        {item.format}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-black font-medium tabular-nums">
                      {item.row_count.toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <span className="text-black/60">
                          {item.verification_hash.slice(0, 10)}...{item.verification_hash.slice(-8)}
                        </span>
                        <button
                          onClick={() => copyToClipboard(item.verification_hash)}
                          title="Copy Full SHA256 Hash"
                          className="p-1 hover:bg-[#EAEAEA] rounded-full text-black/50 hover:text-black cursor-pointer transition-colors"
                        >
                          {copiedHash === item.verification_hash ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-black/50 text-[11px] font-mono">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleDownload(item.id, item.title, item.format)}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[#E5E5E5] hover:border-black bg-white hover:bg-[#F5F5F5] text-black text-xs font-medium transition-colors cursor-pointer"
                      >
                        <Download className="w-3 h-3" />
                        <span>Download</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};
export default ReportsConsole;
