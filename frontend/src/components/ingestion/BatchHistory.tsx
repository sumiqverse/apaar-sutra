import React, { useEffect, useState } from "react";
import {
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Download,
  RefreshCw,
  Search,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { apiClient } from "../../lib/api";

interface BatchItem {
  id: string;
  institution_id: string;
  filename: string;
  file_hash: string;
  source: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  total_rows: number;
  processed_rows: number;
  accepted_rows: number;
  warning_rows: number;
  rejected_rows: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

interface ErrorItem {
  row_number: number;
  column?: string;
  value?: string;
  error_code: string;
  reason: string;
  fix_hint: string;
}

export const BatchHistory: React.FC = () => {
  const [batches, setBatches] = useState<BatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [batchErrors, setBatchErrors] = useState<ErrorItem[]>([]);
  const [loadingErrors, setLoadingErrors] = useState(false);

  const fetchBatches = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient<BatchItem[]>("/api/v1/batches?limit=50");
      setBatches(data);
    } catch (err: any) {
      setError(err.message || "Failed to load upload batches");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBatches();
  }, []);

  const handleDownloadErrors = (batchId: string) => {
    window.location.href = `/api/v1/batches/${batchId}/errors?format=csv`;
  };

  const handleInspectErrors = async (batchId: string) => {
    if (selectedBatchId === batchId) {
      setSelectedBatchId(null);
      setBatchErrors([]);
      return;
    }

    setSelectedBatchId(batchId);
    setLoadingErrors(true);
    try {
      const res = await apiClient<ErrorItem[]>(`/api/v1/batches/${batchId}/errors?format=json`);
      setBatchErrors(res);
    } catch {
      setBatchErrors([]);
    } finally {
      setLoadingErrors(false);
    }
  };

  const filtered = batches.filter((b) =>
    b.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
    b.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Upload Batch Ledger</h2>
          <p className="text-xs text-slate-500">
            Immutable audit record of institutional bulk student ingestion runs and error diagnostics.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Filter by filename or batch ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>

          <button
            onClick={fetchBatches}
            disabled={loading}
            className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-xl flex items-center gap-1.5 transition shadow-sm cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
          {error}
        </div>
      )}

      {loading && batches.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400 text-sm">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-indigo-500" />
          Loading institutional batch history...
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400 text-sm">
          <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 text-slate-300" />
          No upload batches found. Upload your first CSV/XLSX dataset using the Upload Wizard.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((batch) => {
            const isExpanded = selectedBatchId === batch.id;
            return (
              <div
                key={batch.id}
                className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden transition hover:border-slate-300"
              >
                <div className="p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600 shrink-0">
                      <FileSpreadsheet className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-900 text-sm">{batch.filename}</span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            batch.status === "COMPLETED"
                              ? "bg-emerald-100 text-emerald-800"
                              : batch.status === "PROCESSING"
                              ? "bg-indigo-100 text-indigo-800 animate-pulse"
                              : batch.status === "FAILED"
                              ? "bg-red-100 text-red-800"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {batch.status}
                        </span>
                        <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                          {batch.source}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1 font-mono">
                        <span>ID: {batch.id.slice(0, 8)}...</span>
                        <span>•</span>
                        <span>{new Date(batch.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* Metrics Badges */}
                  <div className="flex items-center gap-3 flex-wrap">
                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-50 border border-slate-200 rounded-lg text-xs">
                      <span className="text-slate-500 font-medium">Total:</span>
                      <span className="font-bold text-slate-800">{batch.total_rows}</span>
                    </div>

                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span className="font-bold">{batch.accepted_rows}</span>
                    </div>

                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                      <span className="font-bold">{batch.warning_rows}</span>
                    </div>

                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800">
                      <XCircle className="w-3.5 h-3.5 text-red-600" />
                      <span className="font-bold">{batch.rejected_rows}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 self-end md:self-center">
                    {batch.rejected_rows > 0 && (
                      <button
                        onClick={() => handleDownloadErrors(batch.id)}
                        title="Download CSV Error Report"
                        className="px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-700 text-xs font-semibold rounded-lg flex items-center gap-1 transition cursor-pointer"
                      >
                        <Download className="w-3.5 h-3.5" />
                        CSV Report
                      </button>
                    )}

                    {batch.rejected_rows > 0 && (
                      <button
                        onClick={() => handleInspectErrors(batch.id)}
                        className="px-3 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-lg flex items-center gap-1 transition cursor-pointer"
                      >
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        {isExpanded ? "Hide Errors" : "View Errors"}
                      </button>
                    )}
                  </div>
                </div>

                {/* Inline Error Inspection Drawer */}
                {isExpanded && (
                  <div className="border-t border-slate-200 bg-slate-50/70 p-4 space-y-3">
                    <div className="flex items-center justify-between text-xs text-slate-600">
                      <span className="font-semibold">Diagnostic Failure Analysis (First 50 issues)</span>
                      <button
                        onClick={() => handleDownloadErrors(batch.id)}
                        className="text-indigo-600 hover:underline flex items-center gap-1 font-semibold"
                      >
                        <Download className="w-3 h-3" /> Download complete CSV
                      </button>
                    </div>

                    {loadingErrors ? (
                      <div className="py-6 text-center text-xs text-slate-400">Loading itemized errors...</div>
                    ) : batchErrors.length === 0 ? (
                      <div className="py-4 text-center text-xs text-slate-400">No row errors recorded.</div>
                    ) : (
                      <div className="overflow-x-auto max-h-64 border border-slate-200 rounded-lg bg-white">
                        <table className="w-full text-left text-[11px] divide-y divide-slate-200">
                          <thead className="bg-slate-100 text-slate-700 font-semibold sticky top-0">
                            <tr>
                              <th className="px-3 py-2 w-16">Row</th>
                              <th className="px-3 py-2">Column</th>
                              <th className="px-3 py-2">Input Value</th>
                              <th className="px-3 py-2">Error Code</th>
                              <th className="px-3 py-2">Reason</th>
                              <th className="px-3 py-2">Remediation Hint</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 font-mono text-slate-700">
                            {batchErrors.slice(0, 50).map((err, idx) => (
                              <tr key={idx} className="hover:bg-red-50/40">
                                <td className="px-3 py-1.5 font-bold text-red-600">{err.row_number}</td>
                                <td className="px-3 py-1.5 text-slate-600">{err.column || "-"}</td>
                                <td className="px-3 py-1.5 truncate max-w-[120px]">{err.value || "-"}</td>
                                <td className="px-3 py-1.5 text-red-700 font-bold">{err.error_code}</td>
                                <td className="px-3 py-1.5 font-sans text-slate-800">{err.reason}</td>
                                <td className="px-3 py-1.5 font-sans text-indigo-700 italic">{err.fix_hint}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
