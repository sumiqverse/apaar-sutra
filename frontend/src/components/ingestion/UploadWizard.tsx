import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  Download,
  UploadCloud,
  FileSpreadsheet,
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ArrowRight,
  RefreshCw,
  Eye,
  Filter,
} from "lucide-react";
import { apiClient } from "../../lib/api";

interface ErrorRow {
  row_number: number;
  column?: string;
  value?: string;
  error_code: string;
  reason: string;
  fix_hint: string;
}

interface BatchProgress {
  batch_id: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  processed: number;
  total: number;
  accepted: number;
  warning: number;
  rejected: number;
}

export const UploadWizard: React.FC = () => {
  const { t } = useTranslation();
  const [step, setStep] = useState<number>(1);
  const [file, setFile] = useState<File | null>(null);
  const [previewRows, setPreviewRows] = useState<string[][]>([]);
  const [previewHeaders, setPreviewHeaders] = useState<string[]>([]);
  const [academicYear, setAcademicYear] = useState<string>("2025-26");

  const [batchId, setBatchId] = useState<string | null>(null);
  const [progress, setProgress] = useState<BatchProgress | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [errors, setErrors] = useState<ErrorRow[]>([]);
  const [errorFilter, setErrorFilter] = useState<string>("ALL");
  const eventSourceRef = useRef<EventSource | null>(null);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Step 1: Download Template
  const handleDownloadTemplate = (format: "csv" | "xlsx") => {
    window.location.href = `/api/v1/batches/template?format=${format}`;
  };

  // Step 2: Client-side Preview (First 20 rows of CSV)
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setUploadError(null);

      if (selected.name.endsWith(".csv")) {
        const reader = new FileReader();
        reader.onload = (event) => {
          const text = event.target?.result as string;
          const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
          if (lines.length > 0) {
            const parsed = lines.slice(0, 21).map((line) => line.split(",").map((c) => c.trim()));
            setPreviewHeaders(parsed[0] || []);
            setPreviewRows(parsed.slice(1));
          }
        };
        reader.readAsText(selected.slice(0, 64 * 1024)); // First 64KB for speed
      } else {
        setPreviewHeaders(["File Name", "File Size", "Format"]);
        setPreviewRows([[selected.name, `${(selected.size / (1024 * 1024)).toFixed(2)} MB`, "Excel XLSX (Binary)"]]);
      }
    }
  };

  // Step 3: Upload & Live SSE Progress
  const handleStartUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("academic_year", academicYear);

    try {
      const res = await apiClient<{ batch_id: string; warning?: string }>("/api/v1/batches", {
        method: "POST",
        body: formData,
      });

      const newBatchId = res.batch_id;
      setBatchId(newBatchId);
      setStep(3);

      // Start EventSource for SSE live progress
      const es = new EventSource(`/api/v1/batches/${newBatchId}/events`);
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const data: BatchProgress = JSON.parse(event.data);
          setProgress(data);

          if (data.status === "COMPLETED" || data.status === "FAILED") {
            es.close();
            setIsUploading(false);
            setStep(4);
            fetchBatchErrors(newBatchId);
          }
        } catch (err) {
          console.error("SSE parse error", err);
        }
      };

      es.onerror = () => {
        es.close();
        setIsUploading(false);
      };
    } catch (err: any) {
      setIsUploading(false);
      setUploadError(err.message || "Failed to initiate batch upload.");
    }
  };

  // Step 4: Fetch Diagnostic Errors
  const fetchBatchErrors = async (id: string) => {
    try {
      const errList = await apiClient<ErrorRow[]>(`/api/v1/batches/${id}/errors?format=json`);
      setErrors(errList || []);
    } catch (err) {
      console.error("Failed to load batch errors", err);
    }
  };

  const handleDownloadErrorReport = () => {
    if (!batchId) return;
    window.location.href = `/api/v1/batches/${batchId}/errors?format=csv`;
  };

  const handleReset = () => {
    setStep(1);
    setFile(null);
    setPreviewRows([]);
    setPreviewHeaders([]);
    setBatchId(null);
    setProgress(null);
    setErrors([]);
  };

  const filteredErrors = errors.filter((err) => {
    if (errorFilter === "ALL") return true;
    return err.error_code.includes(errorFilter);
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Wizard Step Stepper */}
      <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
        <div className="flex items-center justify-between max-w-4xl mx-auto">
          {[
            { num: 1, label: t("ingestion.steps.template", "1. Download Template") },
            { num: 2, label: t("ingestion.steps.preview", "2. Drop & Preview") },
            { num: 3, label: t("ingestion.steps.progress", "3. Live Processing") },
            { num: 4, label: t("ingestion.steps.results", "4. Diagnostic Results") },
          ].map((s) => (
            <div key={s.num} className="flex items-center space-x-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                  step === s.num
                    ? "bg-blue-600 text-white shadow-md shadow-blue-200"
                    : step > s.num
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-200 text-slate-600"
                }`}
              >
                {step > s.num ? "✓" : s.num}
              </div>
              <span
                className={`text-sm font-medium ${
                  step === s.num ? "text-blue-900 font-semibold" : "text-slate-600"
                }`}
              >
                {s.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="p-8">
        {/* STEP 1: DOWNLOAD TEMPLATE */}
        {step === 1 && (
          <div className="max-w-2xl mx-auto text-center space-y-6">
            <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto">
              <FileSpreadsheet className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-slate-900">
                {t("ingestion.template.title", "Download Official Ingestion Template")}
              </h3>
              <p className="text-sm text-slate-600 mt-2">
                {t(
                  "ingestion.template.description",
                  "Use the official AICTE template containing the 21 required student identity and enrollment fields, built-in dropdown validations, and data dictionary."
                )}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-4">
              <button
                onClick={() => handleDownloadTemplate("xlsx")}
                className="flex items-center justify-center space-x-3 p-4 border-2 border-emerald-500 bg-emerald-50/50 hover:bg-emerald-100/50 rounded-xl transition font-medium text-emerald-800"
              >
                <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
                <span>Download Excel (.XLSX)</span>
              </button>
              <button
                onClick={() => handleDownloadTemplate("csv")}
                className="flex items-center justify-center space-x-3 p-4 border-2 border-blue-500 bg-blue-50/50 hover:bg-blue-100/50 rounded-xl transition font-medium text-blue-800"
              >
                <FileText className="w-5 h-5 text-blue-600" />
                <span>Download CSV (.CSV)</span>
              </button>
            </div>

            <div className="pt-6">
              <button
                onClick={() => setStep(2)}
                className="inline-flex items-center space-x-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition shadow-sm"
              >
                <span>Continue to Upload</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: DROPZONE & PREVIEW */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Upload Dataset & Inspect Headers</h3>
                <p className="text-sm text-slate-500">Files up to 50,000 rows (max 20 MB). CSV and XLSX supported.</p>
              </div>
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-slate-700">Academic Year:</label>
                <select
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                  className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  <option value="2025-26">2025-26</option>
                  <option value="2024-25">2024-25</option>
                </select>
              </div>
            </div>

            {/* Dropzone */}
            <div className="border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-8 text-center bg-slate-50/50 transition">
              <UploadCloud className="w-12 h-12 text-slate-400 mx-auto mb-3" />
              <input
                type="file"
                id="file-upload"
                accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={handleFileChange}
                className="hidden"
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer inline-flex items-center px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-sm font-medium shadow-sm transition"
              >
                Select CSV or Excel File
              </label>
              {file && (
                <p className="mt-3 text-sm text-blue-600 font-medium">
                  Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>

            {uploadError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-3 text-red-800 text-sm">
                <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            {/* Preview Table */}
            {previewHeaders.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-800 flex items-center space-x-1.5">
                    <Eye className="w-4 h-4 text-slate-500" />
                    <span>Client-Side Sample Preview (First {previewRows.length} rows)</span>
                  </span>
                  <span className="text-xs text-slate-500">Headers detected: {previewHeaders.length}</span>
                </div>
                <div className="overflow-x-auto border border-slate-200 rounded-lg max-h-60">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead className="bg-slate-100 text-slate-700 sticky top-0">
                      <tr>
                        {previewHeaders.map((h, i) => (
                          <th key={i} className="px-3 py-2 border-b border-slate-200 font-semibold whitespace-nowrap">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-600">
                      {previewRows.map((r, ri) => (
                        <tr key={ri} className="hover:bg-slate-50">
                          {r.map((c, ci) => (
                            <td key={ci} className="px-3 py-1.5 whitespace-nowrap">
                              {c}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg text-sm font-medium transition"
              >
                Back
              </button>
              <button
                disabled={!file || isUploading}
                onClick={handleStartUpload}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition shadow-sm flex items-center space-x-2"
              >
                {isUploading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
                <span>Initiate Stream Ingestion</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: LIVE SSE PROGRESS */}
        {step === 3 && (
          <div className="max-w-xl mx-auto py-8 text-center space-y-6">
            <RefreshCw className="w-12 h-12 text-blue-600 animate-spin mx-auto" />
            <div>
              <h3 className="text-lg font-bold text-slate-900">Processing Stream Ingestion</h3>
              <p className="text-sm text-slate-500 mt-1">
                Validating schemas, calculating HMAC blind indexes, and verifying APAAR credentials in batches...
              </p>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
              <div
                className="bg-blue-600 h-full transition-all duration-300"
                style={{
                  width: `${
                    progress?.total && progress.total > 0
                      ? Math.min(100, Math.round((progress.processed / progress.total) * 100))
                      : 65
                  }%`,
                }}
              />
            </div>

            <div className="grid grid-cols-3 gap-4 pt-4 text-sm">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <div className="text-slate-500 text-xs">Processed</div>
                <div className="text-lg font-bold text-slate-900">{progress?.processed ?? 0}</div>
              </div>
              <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200 text-emerald-800">
                <div className="text-xs">Accepted</div>
                <div className="text-lg font-bold">{progress?.accepted ?? 0}</div>
              </div>
              <div className="p-3 bg-red-50 rounded-lg border border-red-200 text-red-800">
                <div className="text-xs">Rejected</div>
                <div className="text-lg font-bold">{progress?.rejected ?? 0}</div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: DIAGNOSTIC RESULTS & ERROR REPORT */}
        {step === 4 && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Batch Ingestion Completed</h3>
                <p className="text-sm text-slate-500">Batch ID: {batchId}</p>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  onClick={handleDownloadErrorReport}
                  className="inline-flex items-center space-x-2 px-4 py-2 border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-sm font-medium transition shadow-sm"
                >
                  <Download className="w-4 h-4 text-slate-500" />
                  <span>Download Error Report (CSV)</span>
                </button>
                <button
                  onClick={handleReset}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition"
                >
                  Upload Another File
                </button>
              </div>
            </div>

            {/* Metrics Cards */}
            <div className="grid grid-cols-4 gap-4">
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
                <div className="text-xs font-medium text-slate-500">Total Rows</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">{progress?.processed ?? 0}</div>
              </div>
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
                <div className="text-xs font-medium text-emerald-700 flex items-center space-x-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Accepted & Verified</span>
                </div>
                <div className="text-2xl font-bold text-emerald-900 mt-1">{progress?.accepted ?? 0}</div>
              </div>
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
                <div className="text-xs font-medium text-amber-700 flex items-center space-x-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Warnings Flagged</span>
                </div>
                <div className="text-2xl font-bold text-amber-900 mt-1">{progress?.warning ?? 0}</div>
              </div>
              <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
                <div className="text-xs font-medium text-red-700 flex items-center space-x-1">
                  <XCircle className="w-3.5 h-3.5" />
                  <span>Rejected Rows</span>
                </div>
                <div className="text-2xl font-bold text-red-900 mt-1">{progress?.rejected ?? 0}</div>
              </div>
            </div>

            {/* Error Table */}
            <div className="border border-slate-200 rounded-xl overflow-hidden bg-white">
              <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <span className="font-semibold text-sm text-slate-800">
                  Validation Issues & Remediation Hints ({filteredErrors.length})
                </span>
                <div className="flex items-center space-x-2">
                  <Filter className="w-4 h-4 text-slate-400" />
                  <select
                    value={errorFilter}
                    onChange={(e) => setErrorFilter(e.target.value)}
                    className="text-xs border border-slate-300 rounded px-2 py-1 bg-white"
                  >
                    <option value="ALL">All Categories</option>
                    <option value="APAAR">APAAR Format / Checksum</option>
                    <option value="DOB">Date of Birth</option>
                    <option value="REGISTRY">Registry Mismatch</option>
                  </select>
                </div>
              </div>

              {filteredErrors.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-sm">
                  No validation errors recorded! All records satisfied schema and APAAR identity checks.
                </div>
              ) : (
                <div className="overflow-x-auto max-h-80">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-100 text-slate-700 sticky top-0">
                      <tr>
                        <th className="px-4 py-2.5 font-semibold">Row #</th>
                        <th className="px-4 py-2.5 font-semibold">Column</th>
                        <th className="px-4 py-2.5 font-semibold">Value</th>
                        <th className="px-4 py-2.5 font-semibold">Error Code</th>
                        <th className="px-4 py-2.5 font-semibold">Reason</th>
                        <th className="px-4 py-2.5 font-semibold">Fix Hint</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-600">
                      {filteredErrors.map((err, i) => (
                        <tr key={i} className="hover:bg-slate-50">
                          <td className="px-4 py-2 font-mono font-bold text-slate-800">{err.row_number}</td>
                          <td className="px-4 py-2 font-mono text-slate-600">{err.column || "-"}</td>
                          <td className="px-4 py-2 font-mono text-slate-700 max-w-xs truncate">{err.value || "-"}</td>
                          <td className="px-4 py-2 font-bold text-red-600">{err.error_code}</td>
                          <td className="px-4 py-2 text-slate-800">{err.reason}</td>
                          <td className="px-4 py-2 text-blue-700 italic">{err.fix_hint}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
