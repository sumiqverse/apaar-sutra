import React, { useState } from "react";
import {
  UserCheck,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Building,
  GraduationCap,
  User,
  Globe,
} from "lucide-react";
import { apiClient } from "../../lib/api";

interface CheckApaarResult {
  valid_format: boolean;
  normalized_id?: string;
  format_warning?: string | null;
  found: boolean;
  status: string;
  name_match_score?: number;
  dob_match?: boolean;
  last_known_institution?: string | null;
  message?: string;
}

interface EnrolSuccessResponse {
  student_id: string;
  enrolment_id: string;
  apaar_id: string;
  masked_apaar_id: string;
  apaar_status: string;
  status: string;
  name_match_score: number;
  dob_match: boolean;
  verification_reason?: string;
}

export const StudentEnrolForm: React.FC = () => {

  // 21 Field Form State
  const [formData, setFormData] = useState({
    apaar_id: "",
    student_ref_id: "",
    name: "",
    dob: "",
    gender: "MALE",
    parent_name: "",
    email: "",
    phone: "",
    address: "",
    program_name: "Bachelor of Technology in Computer Science",
    branch: "Computer Science and Engineering",
    academic_year: "2025-26",
    admission_category: "GEN",
    quota_type: "REGULAR",
    is_nri: false,
    sponsor_name: "",
    sponsor_relation: "",
    oci_status: false,
    is_foreign_national: false,
    nationality: "INDIAN",
    admission_date: new Date().toISOString().split("T")[0],
    status: "ACTIVE",
  });

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [isCheckingApaar, setIsCheckingApaar] = useState(false);
  const [apaarCheckResult, setApaarCheckResult] = useState<CheckApaarResult | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [enrolSuccess, setEnrolSuccess] = useState<EnrolSuccessResponse | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    if (type === "checkbox") {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData((prev) => ({ ...prev, [name]: checked }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }

    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }

    if (name === "apaar_id") {
      setApaarCheckResult(null);
    }
  };

  const handleCheckApaar = async () => {
    if (!formData.apaar_id.trim()) {
      setFieldErrors((prev) => ({ ...prev, apaar_id: "APAAR ID is required" }));
      return;
    }
    setIsCheckingApaar(true);
    setApaarCheckResult(null);
    try {
      const res = await apiClient<CheckApaarResult>("/api/v1/students/check-apaar", {
        method: "POST",
        body: JSON.stringify({
          apaar_id: formData.apaar_id,
          name: formData.name || undefined,
          dob: formData.dob || undefined,
        }),
      });
      setApaarCheckResult(res);
      if (!res.valid_format) {
        setFieldErrors((prev) => ({ ...prev, apaar_id: res.message || "Invalid APAAR format" }));
      }
    } catch (err: any) {
      setApaarCheckResult({
        valid_format: false,
        found: false,
        status: "ERROR",
        message: err.message || "APAAR verification service unreachable",
      });
    } finally {
      setIsCheckingApaar(false);
    }
  };

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!formData.apaar_id.trim()) errors.apaar_id = "APAAR ID is mandatory";
    if (!formData.student_ref_id.trim()) errors.student_ref_id = "Student Roll / Ref ID is required";
    if (!formData.name.trim()) errors.name = "Full Legal Name is required";
    if (!formData.dob) errors.dob = "Date of Birth is required";
    if (!formData.academic_year.match(/^\d{4}-\d{2}$/)) errors.academic_year = "Format must be YYYY-YY (e.g. 2025-26)";
    if (!formData.admission_date) errors.admission_date = "Admission Date is required";
    if (formData.is_nri && !formData.sponsor_name.trim()) {
      errors.sponsor_name = "Sponsor Name required for NRI quota";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setSubmitError(null);

    const payload = {
      apaar_id: formData.apaar_id,
      student_ref_id: formData.student_ref_id,
      name: formData.name,
      dob: formData.dob,
      gender: formData.gender,
      parent_name: formData.parent_name || undefined,
      contact: {
        email: formData.email,
        phone: formData.phone,
        address: formData.address,
      },
      program_name: formData.program_name,
      branch: formData.branch,
      academic_year: formData.academic_year,
      admission_category: formData.admission_category,
      quota_type: formData.quota_type,
      is_nri: formData.is_nri,
      sponsor_details: formData.is_nri
        ? { sponsor_name: formData.sponsor_name, relationship: formData.sponsor_relation }
        : undefined,
      oci_status: formData.oci_status,
      is_foreign_national: formData.is_foreign_national,
      nationality: formData.nationality,
      admission_date: formData.admission_date,
      status: formData.status,
    };

    try {
      const res = await apiClient<EnrolSuccessResponse>("/api/v1/students/enrol", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setEnrolSuccess(res);
    } catch (err: any) {
      setSubmitError(err.message || "Failed to enrol student. Please verify the fields.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setEnrolSuccess(null);
    setFormData({
      apaar_id: "",
      student_ref_id: "",
      name: "",
      dob: "",
      gender: "MALE",
      parent_name: "",
      email: "",
      phone: "",
      address: "",
      program_name: "Bachelor of Technology in Computer Science",
      branch: "Computer Science and Engineering",
      academic_year: "2025-26",
      admission_category: "GEN",
      quota_type: "REGULAR",
      is_nri: false,
      sponsor_name: "",
      sponsor_relation: "",
      oci_status: false,
      is_foreign_national: false,
      nationality: "INDIAN",
      admission_date: new Date().toISOString().split("T")[0],
      status: "ACTIVE",
    });
    setApaarCheckResult(null);
    setFieldErrors({});
    setSubmitError(null);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-indigo-700 via-indigo-800 to-slate-900 rounded-2xl p-6 text-white shadow-xl flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/30 text-indigo-200 border border-indigo-400/30">
              Direct Registration
            </span>
            <span className="text-xs text-indigo-300">End-to-End 21 Fields</span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight">Single Student Enrolment</h2>
          <p className="text-sm text-indigo-200">
            Cryptographically secure student onboarding with real-time APAAR verification and audit logging.
          </p>
        </div>
        <div className="hidden sm:flex h-12 w-12 rounded-xl bg-white/10 items-center justify-center border border-white/20">
          <GraduationCap className="h-6 w-6 text-indigo-200" />
        </div>
      </div>

      {enrolSuccess ? (
        <div className="bg-white rounded-2xl border border-emerald-200 p-8 shadow-sm space-y-6 text-center animate-in fade-in zoom-in-95 duration-200">
          <div className="mx-auto w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 shadow-inner">
            <CheckCircle2 className="w-10 h-10" />
          </div>
          <div className="space-y-2">
            <h3 className="text-2xl font-bold text-slate-900">Enrolment Successfully Recorded!</h3>
            <p className="text-slate-600 max-w-md mx-auto text-sm">
              The student profile and admission record have been verified and sealed in the academic ledger.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl mx-auto text-left text-xs bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div>
              <span className="text-slate-400 block font-medium">Masked APAAR</span>
              <span className="text-slate-800 font-mono font-bold text-sm">{enrolSuccess.masked_apaar_id}</span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">APAAR Status</span>
              <span className={`inline-block px-2 py-0.5 rounded font-bold text-[11px] ${
                enrolSuccess.apaar_status === "VERIFIED"
                  ? "bg-emerald-100 text-emerald-800"
                  : enrolSuccess.apaar_status === "PENDING"
                  ? "bg-amber-100 text-amber-800"
                  : "bg-red-100 text-red-800"
              }`}>
                {enrolSuccess.apaar_status}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Name Match</span>
              <span className="text-slate-800 font-bold">{enrolSuccess.name_match_score}%</span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">DOB Verified</span>
              <span className="text-slate-800 font-bold">{enrolSuccess.dob_match ? "Matched" : "Unverified"}</span>
            </div>
          </div>

          <div className="pt-4 flex justify-center gap-4">
            <button
              onClick={resetForm}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-xl shadow transition cursor-pointer"
            >
              Enrol Another Student
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-8 bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
          {submitError && (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 flex items-start gap-3 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Enrolment Submission Failed</p>
                <p>{submitError}</p>
              </div>
            </div>
          )}

          {/* Section 1: APAAR & Identity */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <ShieldCheck className="w-5 h-5 text-indigo-600" />
              <h3 className="text-base font-semibold text-slate-900">1. APAAR Academic Identity & Verification</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
              <div className="md:col-span-2 space-y-1">
                <label className="block text-xs font-semibold text-slate-700">
                  12-Digit APAAR ID <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    name="apaar_id"
                    value={formData.apaar_id}
                    onChange={handleChange}
                    placeholder="e.g. 123456789012 (Hindi numerals allowed: १२३४...)"
                    className={`flex-1 px-3 py-2 border rounded-xl text-sm font-mono focus:ring-2 focus:ring-indigo-500 outline-none ${
                      fieldErrors.apaar_id ? "border-red-300 bg-red-50" : "border-slate-300"
                    }`}
                  />
                  <button
                    type="button"
                    onClick={handleCheckApaar}
                    disabled={isCheckingApaar || !formData.apaar_id}
                    className="px-4 py-2 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition cursor-pointer"
                  >
                    {isCheckingApaar ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserCheck className="w-4 h-4" />}
                    Check APAAR
                  </button>
                </div>
                {fieldErrors.apaar_id && (
                  <p className="text-xs text-red-600 flex items-center gap-1 mt-1">
                    <AlertCircle className="w-3.5 h-3.5" /> {fieldErrors.apaar_id}
                  </p>
                )}
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">
                  Institution Student Ref / Roll No <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="student_ref_id"
                  value={formData.student_ref_id}
                  onChange={handleChange}
                  placeholder="e.g. 2025/CS/042"
                  className={`w-full px-3 py-2 border rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none ${
                    fieldErrors.student_ref_id ? "border-red-300 bg-red-50" : "border-slate-300"
                  }`}
                />
                {fieldErrors.student_ref_id && (
                  <p className="text-xs text-red-600 flex items-center gap-1 mt-1">{fieldErrors.student_ref_id}</p>
                )}
              </div>
            </div>

            {/* APAAR Real-time Pre-check Diagnostic Card */}
            {apaarCheckResult && (
              <div
                className={`p-3.5 rounded-xl border text-xs space-y-1.5 ${
                  apaarCheckResult.status === "ACTIVE" || apaarCheckResult.status === "VERIFIED"
                    ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                    : apaarCheckResult.status === "PENDING"
                    ? "bg-amber-50 border-amber-200 text-amber-800"
                    : "bg-red-50 border-red-200 text-red-800"
                }`}
              >
                <div className="flex items-center justify-between font-semibold">
                  <span className="flex items-center gap-1.5">
                    {apaarCheckResult.found ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                    )}
                    Registry Status: {apaarCheckResult.status}
                  </span>
                  {apaarCheckResult.name_match_score !== undefined && (
                    <span>Name Match Score: {apaarCheckResult.name_match_score}%</span>
                  )}
                </div>
                {apaarCheckResult.format_warning && (
                  <p className="text-amber-700 font-medium">⚠️ {apaarCheckResult.format_warning}</p>
                )}
                {apaarCheckResult.last_known_institution && (
                  <p className="text-slate-600">
                    Prior Registered Institution: <b>{apaarCheckResult.last_known_institution}</b>
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Section 2: Personal Profile */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <User className="w-5 h-5 text-indigo-600" />
              <h3 className="text-base font-semibold text-slate-900">2. Personal Profile & Cryptographic Vault</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="md:col-span-2 space-y-1">
                <label className="block text-xs font-semibold text-slate-700">
                  Full Legal Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Official name matching Aadhaar / Class X certificate"
                  className={`w-full px-3 py-2 border rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none ${
                    fieldErrors.name ? "border-red-300 bg-red-50" : "border-slate-300"
                  }`}
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">
                  Date of Birth <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  name="dob"
                  value={formData.dob}
                  onChange={handleChange}
                  className={`w-full px-3 py-2 border rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none ${
                    fieldErrors.dob ? "border-red-300 bg-red-50" : "border-slate-300"
                  }`}
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Gender</label>
                <select
                  name="gender"
                  value={formData.gender}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none bg-white"
                >
                  <option value="MALE">Male</option>
                  <option value="FEMALE">Female</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div className="md:col-span-2 space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Parent / Guardian Name</label>
                <input
                  type="text"
                  name="parent_name"
                  value={formData.parent_name}
                  onChange={handleChange}
                  placeholder="Father's or Mother's legal name"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Email Address</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="student@example.edu"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Phone Number</label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="+91 9876543210"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="md:col-span-4 space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Permanent Residential Address</label>
                <input
                  type="text"
                  name="address"
                  value={formData.address}
                  onChange={handleChange}
                  placeholder="Street, District, State, Postal Code"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Academic Program & Year */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <Building className="w-5 h-5 text-indigo-600" />
              <h3 className="text-base font-semibold text-slate-900">3. Academic Program & Intake Stream</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Program Name</label>
                <input
                  type="text"
                  name="program_name"
                  value={formData.program_name}
                  onChange={handleChange}
                  placeholder="e.g. Bachelor of Technology"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Branch / Specialization</label>
                <input
                  type="text"
                  name="branch"
                  value={formData.branch}
                  onChange={handleChange}
                  placeholder="e.g. Computer Science and Engineering"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">
                  Academic Year <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="academic_year"
                  value={formData.academic_year}
                  onChange={handleChange}
                  placeholder="2025-26"
                  className={`w-full px-3 py-2 border rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none ${
                    fieldErrors.academic_year ? "border-red-300 bg-red-50" : "border-slate-300"
                  }`}
                />
              </div>
            </div>
          </div>

          {/* Section 4: Categorization, Quotas & International Rules */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-slate-200">
              <Globe className="w-5 h-5 text-indigo-600" />
              <h3 className="text-base font-semibold text-slate-900">4. Quotas, Reservation & International Status</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Admission Category</label>
                <select
                  name="admission_category"
                  value={formData.admission_category}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none bg-white"
                >
                  <option value="GEN">General (GEN)</option>
                  <option value="EWS">Economically Weaker (EWS)</option>
                  <option value="OBC">Other Backward Class (OBC)</option>
                  <option value="SC">Scheduled Caste (SC)</option>
                  <option value="ST">Scheduled Tribe (ST)</option>
                  <option value="PWD">Persons with Disabilities (PWD)</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Admission Quota Type</label>
                <select
                  name="quota_type"
                  value={formData.quota_type}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none bg-white"
                >
                  <option value="REGULAR">Regular Approved Intake</option>
                  <option value="SUPERNUMERARY">Supernumerary (15% Cap)</option>
                  <option value="NRI">Non-Resident Indian (NRI)</option>
                  <option value="OCI">Overseas Citizen of India (OCI)</option>
                  <option value="FN">Foreign National (FN)</option>
                  <option value="TFW">Tuition Fee Waiver (TFW)</option>
                  <option value="OTHER">Other Quota</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Nationality</label>
                <input
                  type="text"
                  name="nationality"
                  value={formData.nationality}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">Admission Date</label>
                <input
                  type="date"
                  name="admission_date"
                  value={formData.admission_date}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
            </div>

            {/* NRI / Supernumerary Toggles */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700">
                  <input
                    type="checkbox"
                    name="is_nri"
                    checked={formData.is_nri}
                    onChange={handleChange}
                    className="rounded text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                  />
                  <span>NRI Student</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700">
                  <input
                    type="checkbox"
                    name="oci_status"
                    checked={formData.oci_status}
                    onChange={handleChange}
                    className="rounded text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                  />
                  <span>OCI Card Holder</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-700">
                  <input
                    type="checkbox"
                    name="is_foreign_national"
                    checked={formData.is_foreign_national}
                    onChange={handleChange}
                    className="rounded text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                  />
                  <span>Foreign National</span>
                </label>
              </div>

              {formData.is_nri && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-200">
                  <div className="space-y-1">
                    <label className="block text-xs font-semibold text-slate-700">
                      Sponsor Full Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="sponsor_name"
                      value={formData.sponsor_name}
                      onChange={handleChange}
                      placeholder="e.g. Ramesh Kumar"
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="block text-xs font-semibold text-slate-700">Sponsor Relationship</label>
                    <input
                      type="text"
                      name="sponsor_relation"
                      value={formData.sponsor_relation}
                      onChange={handleChange}
                      placeholder="e.g. Uncle / Parent"
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Form Actions */}
          <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={resetForm}
              className="px-5 py-2.5 border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-xl transition cursor-pointer"
            >
              Reset Form
            </button>

            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-semibold text-sm rounded-xl shadow transition flex items-center gap-2 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Encrypting & Registering...
                </>
              ) : (
                <>
                  <UserCheck className="w-4 h-4" />
                  Submit Enrolment
                </>
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
