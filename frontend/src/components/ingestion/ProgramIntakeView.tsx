import React, { useEffect, useState } from "react";
import {
  Building2,
  Plus,
  RefreshCw,
  Edit2,
  Sliders,
  ShieldAlert,
} from "lucide-react";
import { apiClient } from "../../lib/api";

interface ProgramIntake {
  program_id: string;
  program_name: string;
  level: string;
  branch: string;
  academic_year: string;
  approved_intake: number;
  supernumerary_seats: number;
  supernumerary_cap_pct: number;
  actual_enrolment: number;
  declared_enrolment?: number | null;
  capacity_status: "WITHIN_CAPACITY" | "WARNING_NEAR_CAPACITY" | "CAPACITY_EXCEEDED";
  utilization_pct: number;
}

export const ProgramIntakeView: React.FC = () => {
  const [programs, setPrograms] = useState<ProgramIntake[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [academicYear, setAcademicYear] = useState<string>("2025-26");

  // Declaration Modal State
  const [showModal, setShowModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    program_id: "",
    program_name: "Bachelor of Technology in Computer Science",
    level: "UG",
    branch: "Computer Science and Engineering",
    academic_year: "2025-26",
    approved_intake: 60,
    supernumerary_seats: 9,
    supernumerary_cap_pct: 15.0,
    declared_enrolment: 65,
  });

  const fetchIntakeSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient<ProgramIntake[]>(
        `/api/v1/programs/intake-summary?academic_year=${academicYear}`
      );
      setPrograms(data);
    } catch (err: any) {
      setError(err.message || "Failed to load program intake data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntakeSummary();
  }, [academicYear]);

  const handleOpenDeclare = (prog?: ProgramIntake) => {
    if (prog) {
      setFormData({
        program_id: prog.program_id,
        program_name: prog.program_name,
        level: prog.level,
        branch: prog.branch,
        academic_year: prog.academic_year,
        approved_intake: prog.approved_intake,
        supernumerary_seats: prog.supernumerary_seats,
        supernumerary_cap_pct: prog.supernumerary_cap_pct,
        declared_enrolment: prog.declared_enrolment || prog.actual_enrolment,
      });
    } else {
      setFormData({
        program_id: "",
        program_name: "Bachelor of Technology in Computer Science",
        level: "UG",
        branch: "Computer Science and Engineering",
        academic_year: academicYear,
        approved_intake: 60,
        supernumerary_seats: 9,
        supernumerary_cap_pct: 15.0,
        declared_enrolment: 60,
      });
    }
    setFormError(null);
    setShowModal(true);
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    if (type === "number") {
      setFormData((prev) => ({ ...prev, [name]: parseFloat(value) || 0 }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setFormError(null);

    // AICTE Rule validation: supernumerary seats <= approved_intake * cap_pct / 100
    const maxSupernumerary = Math.floor((formData.approved_intake * formData.supernumerary_cap_pct) / 100);
    if (formData.supernumerary_seats > maxSupernumerary) {
      setFormError(
        `Supernumerary seats (${formData.supernumerary_seats}) exceed AICTE statutory cap of ${formData.supernumerary_cap_pct}% (${maxSupernumerary} seats).`
      );
      setIsSubmitting(false);
      return;
    }

    try {
      await apiClient("/api/v1/programs/intake-declaration", {
        method: "POST",
        body: JSON.stringify({
          program_id: formData.program_id || undefined,
          program_name: formData.program_name,
          level: formData.level,
          branch: formData.branch,
          academic_year: formData.academic_year,
          approved_intake: formData.approved_intake,
          supernumerary_seats: formData.supernumerary_seats,
          supernumerary_cap_pct: formData.supernumerary_cap_pct,
          declared_enrolment: formData.declared_enrolment,
        }),
      });
      setShowModal(false);
      fetchIntakeSummary();
    } catch (err: any) {
      setFormError(err.message || "Failed to declare program intake quotas");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Academic Program Intake & Quota Declarations
          </h2>
          <p className="text-xs text-slate-500">
            AICTE approved seat capacity, supernumerary quotas (15% statutory cap), and computed utilization.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={academicYear}
            onChange={(e) => setAcademicYear(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-xl text-xs font-medium bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
          >
            <option value="2025-26">AY 2025-26</option>
            <option value="2024-25">AY 2024-25</option>
            <option value="2023-24">AY 2023-24</option>
          </select>

          <button
            onClick={() => handleOpenDeclare()}
            className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition shadow cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            Declare Intake
          </button>

          <button
            onClick={fetchIntakeSummary}
            disabled={loading}
            className="p-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-xl transition cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
          {error}
        </div>
      )}

      {/* Grid of Program Cards */}
      {loading && programs.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400 text-sm">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-indigo-500" />
          Loading program capacity statistics...
        </div>
      ) : programs.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400 text-sm">
          <Building2 className="w-12 h-12 mx-auto mb-3 text-slate-300" />
          No academic programs declared for Academic Year {academicYear}. Click "Declare Intake" to configure your programs.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {programs.map((prog) => {
            const totalCapacity = prog.approved_intake + prog.supernumerary_seats;
            const isExceeded = prog.actual_enrolment > totalCapacity;
            const isNearCap = prog.utilization_pct >= 90.0 && !isExceeded;

            return (
              <div
                key={prog.program_id}
                className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4 hover:border-slate-300 transition flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-100">
                      {prog.level}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        isExceeded
                          ? "bg-red-100 text-red-800"
                          : isNearCap
                          ? "bg-amber-100 text-amber-800"
                          : "bg-emerald-100 text-emerald-800"
                      }`}
                    >
                      {prog.capacity_status.replace(/_/g, " ")}
                    </span>
                  </div>

                  <div>
                    <h3 className="font-bold text-slate-900 text-sm leading-snug">{prog.program_name}</h3>
                    <p className="text-xs text-slate-500">{prog.branch}</p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500 font-medium">Enrolment Utilization</span>
                    <span className="font-bold text-slate-800">{prog.utilization_pct}%</span>
                  </div>
                  <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 rounded-full ${
                        isExceeded
                          ? "bg-red-500"
                          : isNearCap
                          ? "bg-amber-500"
                          : "bg-indigo-600"
                      }`}
                      style={{ width: `${Math.min(prog.utilization_pct, 100)}%` }}
                    />
                  </div>
                </div>

                {/* Metric Columns */}
                <div className="grid grid-cols-3 gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200 text-center text-xs">
                  <div>
                    <span className="text-slate-400 block text-[10px] font-medium">Approved</span>
                    <span className="font-bold text-slate-800 text-sm">{prog.approved_intake}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] font-medium">Supernumerary</span>
                    <span className="font-bold text-indigo-700 text-sm">+{prog.supernumerary_seats}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] font-medium">Enrolled</span>
                    <span
                      className={`font-bold text-sm ${
                        isExceeded ? "text-red-600" : "text-emerald-700"
                      }`}
                    >
                      {prog.actual_enrolment}
                    </span>
                  </div>
                </div>

                {/* Update Button */}
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400">Total Max: {totalCapacity} seats</span>
                  <button
                    onClick={() => handleOpenDeclare(prog)}
                    className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                    Edit Quota
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Declaration / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-6 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-indigo-600" />
                <h3 className="font-bold text-slate-900 text-base">
                  {formData.program_id ? "Update Program Intake Quota" : "Declare Academic Program Intake"}
                </h3>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold cursor-pointer"
              >
                &times;
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-start gap-2">
                <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Program Name</label>
                <input
                  type="text"
                  name="program_name"
                  value={formData.program_name}
                  onChange={handleFormChange}
                  required
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-slate-700">Degree Level</label>
                  <select
                    name="level"
                    value={formData.level}
                    onChange={handleFormChange}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white outline-none"
                  >
                    <option value="UG">Undergraduate (UG)</option>
                    <option value="PG">Postgraduate (PG)</option>
                    <option value="DIPLOMA">Diploma</option>
                    <option value="PGDM">Standalone PGDM</option>
                    <option value="PHD">Doctoral (PhD)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-slate-700">Branch / Specialization</label>
                  <input
                    type="text"
                    name="branch"
                    value={formData.branch}
                    onChange={handleFormChange}
                    required
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-slate-700">Approved Intake</label>
                  <input
                    type="number"
                    name="approved_intake"
                    value={formData.approved_intake}
                    onChange={handleFormChange}
                    min={1}
                    required
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-slate-700">Supernumerary</label>
                  <input
                    type="number"
                    name="supernumerary_seats"
                    value={formData.supernumerary_seats}
                    onChange={handleFormChange}
                    min={0}
                    required
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-slate-700">Cap Percentage</label>
                  <input
                    type="number"
                    name="supernumerary_cap_pct"
                    value={formData.supernumerary_cap_pct}
                    onChange={handleFormChange}
                    min={0}
                    max={100}
                    step={0.5}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>
              </div>

              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-800 space-y-1">
                <p className="font-semibold">AICTE Statutory Quota Rule</p>
                <p>
                  Supernumerary seats (NRI, PIO, FN, EWS, TFW) are capped at {formData.supernumerary_cap_pct}% of approved intake (Max{" "}
                  <b>{Math.floor((formData.approved_intake * formData.supernumerary_cap_pct) / 100)}</b> seats).
                </p>
              </div>

              <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-xl transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white text-xs font-semibold rounded-xl shadow transition cursor-pointer"
                >
                  {isSubmitting ? "Saving Quota..." : "Save Intake Quota"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
