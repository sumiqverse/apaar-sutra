import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  KpiStrip,
  KpiData,
} from "@/components/dashboard/KpiStrip";
import {
  IndiaChoropleth,
  StateData,
} from "@/components/dashboard/IndiaChoropleth";
import {
  FilterBar,
  FilterState,
} from "@/components/dashboard/FilterBar";
import {
  InstitutionLeaderboard,
  LeaderboardRow,
} from "@/components/dashboard/InstitutionLeaderboard";
import { InstitutionDrilldownModal } from "@/components/dashboard/InstitutionDrilldownModal";
import { LiveAlertFeed } from "@/components/dashboard/LiveAlertFeed";
import {
  KpiStripSkeleton,
  MapSkeleton,
  TableSkeleton,
} from "@/components/dashboard/SkeletonLoaders";
import { api } from "@/lib/api";
import { Shield, RefreshCw } from "lucide-react";

export const Dashboard: React.FC = () => {
  const { t } = useTranslation();

  // State management
  const [filters, setFilters] = useState<FilterState>({
    academicYear: "2025-26",
    stateCode: "",
    institutionType: "",
    programLevel: "",
    search: "",
  });

  const [kpis, setKpis] = useState<KpiData>({
    institutions_reporting_pct: 92.4,
    total_enrolments: 1248390,
    intake_utilisation_pct: 88.6,
    open_critical_alerts: 14,
    duplicates_detected: 42,
    verified_records_pct: 94.8,
    total_institutions: 4120,
    reporting_institutions: 3807,
    total_approved_intake: 1408000,
  });

  const [stateMetrics, setStateMetrics] = useState<StateData[]>([]);
  const [leaderboardItems, setLeaderboardItems] = useState<LeaderboardRow[]>([]);
  const [totalInstitutions, setTotalInstitutions] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedInstId, setSelectedInstId] = useState<string | null>(null);

  const [loadingKpis, setLoadingKpis] = useState(true);
  const [loadingMap, setLoadingMap] = useState(true);
  const [loadingTable, setLoadingTable] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // States catalog for filter dropdown
  const statesList = [
    { code: "MH", name: "Maharashtra" },
    { code: "DL", name: "Delhi" },
    { code: "KA", name: "Karnataka" },
    { code: "TN", name: "Tamil Nadu" },
    { code: "UP", name: "Uttar Pradesh" },
    { code: "GJ", name: "Gujarat" },
    { code: "WB", name: "West Bengal" },
    { code: "TG", name: "Telangana" },
    { code: "RJ", name: "Rajasthan" },
    { code: "KL", name: "Kerala" },
    { code: "MP", name: "Madhya Pradesh" },
    { code: "AP", name: "Andhra Pradesh" },
    { code: "PB", name: "Punjab" },
    { code: "OD", name: "Odisha" },
    { code: "BR", name: "Bihar" },
    { code: "HR", name: "Haryana" },
  ];

  // Fetch KPIs
  const loadKpis = async () => {
    try {
      const res = await api.get<KpiData>("/api/v1/analytics/kpis", {
        params: {
          academic_year: filters.academicYear,
          institution_type: filters.institutionType || undefined,
        },
      });
      if (res.data) setKpis(res.data);
    } catch (err) {
      // Keep state defaults
    } finally {
      setLoadingKpis(false);
    }
  };

  // Fetch State Choropleth Data
  const loadChoropleth = async () => {
    try {
      const res = await api.get<{ items: StateData[] }>("/api/v1/analytics/state-choropleth", {
        params: { academic_year: filters.academicYear },
      });
      if (res.data?.items) {
        setStateMetrics(res.data.items);
      }
    } catch (err) {
      // Fallback seeded demo data
      setStateMetrics([
        { state_id: "s1", state_code: "MH", state_name: "Maharashtra", intake_utilisation_pct: 94.2, violation_count: 12, risk_score: 72.4, risk_level: "HIGH", institutions_count: 480, total_enrolments: 142000, approved_intake: 150000 },
        { state_id: "s2", state_code: "DL", state_name: "Delhi", intake_utilisation_pct: 98.1, violation_count: 5, risk_score: 42.0, risk_level: "MEDIUM", institutions_count: 120, total_enrolments: 52000, approved_intake: 53000 },
        { state_id: "s3", state_code: "KA", state_name: "Karnataka", intake_utilisation_pct: 88.5, violation_count: 8, risk_score: 55.0, risk_level: "MEDIUM", institutions_count: 360, total_enrolments: 98000, approved_intake: 110000 },
        { state_id: "s4", state_code: "TN", state_name: "Tamil Nadu", intake_utilisation_pct: 89.0, violation_count: 14, risk_score: 68.0, risk_level: "HIGH", institutions_count: 520, total_enrolments: 135000, approved_intake: 152000 },
        { state_id: "s5", state_code: "UP", state_name: "Uttar Pradesh", intake_utilisation_pct: 91.2, violation_count: 22, risk_score: 84.5, risk_level: "CRITICAL", institutions_count: 610, total_enrolments: 172000, approved_intake: 188000 },
        { state_id: "s6", state_code: "GJ", state_name: "Gujarat", intake_utilisation_pct: 84.0, violation_count: 4, risk_score: 32.0, risk_level: "LOW", institutions_count: 240, total_enrolments: 68000, approved_intake: 81000 },
        { state_id: "s7", state_code: "TG", state_name: "Telangana", intake_utilisation_pct: 92.0, violation_count: 6, risk_score: 48.0, risk_level: "MEDIUM", institutions_count: 280, total_enrolments: 84000, approved_intake: 91000 },
        { state_id: "s8", state_code: "RJ", state_name: "Rajasthan", intake_utilisation_pct: 81.0, violation_count: 9, risk_score: 61.0, risk_level: "HIGH", institutions_count: 210, total_enrolments: 54000, approved_intake: 66000 },
      ]);
    } finally {
      setLoadingMap(false);
    }
  };

  // Fetch Leaderboard
  const loadLeaderboard = async () => {
    setLoadingTable(true);
    try {
      const res = await api.get<{ total: number; items: LeaderboardRow[] }>(
        "/api/v1/analytics/leaderboard",
        {
          params: {
            academic_year: filters.academicYear,
            institution_type: filters.institutionType || undefined,
            program_level: filters.programLevel || undefined,
            search: filters.search || undefined,
            page: currentPage,
            page_size: 10,
          },
        }
      );
      if (res.data) {
        setLeaderboardItems(res.data.items);
        setTotalInstitutions(res.data.total);
      }
    } catch (err) {
      // Fallback demo institutions
      setLeaderboardItems([
        {
          id: "inst-1",
          aicte_id: "1-AN-001",
          name: "Pune Institute of Technology",
          state_name: "Maharashtra",
          state_code: "MH",
          institution_type: "AUTONOMOUS",
          approved_intake: 300,
          enrolment_count: 342,
          utilisation_pct: 114.0,
          risk_score: 88.5,
          risk_level: "CRITICAL",
          open_issues_count: 5,
          critical_issues_count: 2,
          top_contributing_factor: "Enrolment grew 180% YoY vs peer median 6%",
          status: "ACTIVE",
        },
        {
          id: "inst-2",
          aicte_id: "1-UP-102",
          name: "Lucknow Technical University",
          state_name: "Uttar Pradesh",
          state_code: "UP",
          institution_type: "UNIVERSITY",
          approved_intake: 600,
          enrolment_count: 650,
          utilisation_pct: 108.3,
          risk_score: 82.0,
          risk_level: "CRITICAL",
          open_issues_count: 8,
          critical_issues_count: 3,
          top_contributing_factor: "Admission burst: 42% on final cutoff date",
          status: "ACTIVE",
        },
        {
          id: "inst-3",
          aicte_id: "1-DL-002",
          name: "Delhi Engineering College",
          state_name: "Delhi",
          state_code: "DL",
          institution_type: "AFFILIATED",
          approved_intake: 240,
          enrolment_count: 236,
          utilisation_pct: 98.3,
          risk_score: 42.0,
          risk_level: "MEDIUM",
          open_issues_count: 2,
          critical_issues_count: 0,
          top_contributing_factor: "Normal quota distribution",
          status: "ACTIVE",
        },
        {
          id: "inst-4",
          aicte_id: "1-KA-044",
          name: "Bengaluru College of Engineering",
          state_name: "Karnataka",
          state_code: "KA",
          institution_type: "AUTONOMOUS",
          approved_intake: 480,
          enrolment_count: 460,
          utilisation_pct: 95.8,
          risk_score: 38.0,
          risk_level: "MEDIUM",
          open_issues_count: 1,
          critical_issues_count: 0,
          top_contributing_factor: "Compliant peer alignment",
          status: "ACTIVE",
        },
      ]);
      setTotalInstitutions(4);
    } finally {
      setLoadingTable(false);
    }
  };

  useEffect(() => {
    loadKpis();
    loadChoropleth();
  }, [filters.academicYear, filters.institutionType]);

  useEffect(() => {
    loadLeaderboard();
  }, [filters, currentPage]);

  const handleRefreshAll = async () => {
    setRefreshing(true);
    await Promise.all([loadKpis(), loadChoropleth(), loadLeaderboard()]);
    setRefreshing(false);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto" role="region" aria-label="AICTE National Directorate">
      {/* Executive Page Title & Telemetry Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
              <Shield className="h-3.5 w-3.5" />
              AICTE National Directorate
            </span>
            <span className="text-xs text-slate-400">• Academic Year {filters.academicYear}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            {t("dashboard.title", "APAAR National Verification & Capacity Registry")}
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time enrollment telemetry, AI anomaly detection, and statutory quota compliance
          </p>
        </div>

        <button
          type="button"
          onClick={handleRefreshAll}
          disabled={refreshing}
          className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 shadow-sm transition-all"
        >
          <RefreshCw className={`h-3.5 w-3.5 text-brand-600 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "Refreshing..." : "Refresh Telemetry"}
        </button>
      </div>

      {/* 1. Executive KPI Strip */}
      {loadingKpis ? <KpiStripSkeleton /> : <KpiStrip data={kpis} />}

      {/* 2. Multi-Faceted Filters & Saved Views */}
      <FilterBar
        filters={filters}
        onChange={(updated) => {
          setFilters((prev) => ({ ...prev, ...updated }));
          setCurrentPage(1);
        }}
        onReset={() => {
          setFilters({
            academicYear: "2025-26",
            stateCode: "",
            institutionType: "",
            programLevel: "",
            search: "",
          });
          setCurrentPage(1);
        }}
        statesList={statesList}
      />

      {/* 3. Middle Grid: India Map Choropleth + Live Alert Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Interactive India Vector Choropleth (7 cols) */}
        <div className="lg:col-span-7">
          {loadingMap ? (
            <MapSkeleton />
          ) : (
            <IndiaChoropleth
              data={stateMetrics}
              selectedStateCode={filters.stateCode || null}
              onSelectState={(code) => {
                setFilters((prev) => ({ ...prev, stateCode: code || "" }));
                setCurrentPage(1);
              }}
            />
          )}
        </div>

        {/* Live SSE Alert Feed & Workflow (5 cols) */}
        <div className="lg:col-span-5">
          <LiveAlertFeed />
        </div>
      </div>

      {/* 4. Bottom Grid: Institution Anomaly Leaderboard */}
      {loadingTable ? (
        <TableSkeleton />
      ) : (
        <InstitutionLeaderboard
          items={leaderboardItems}
          total={totalInstitutions}
          page={currentPage}
          pageSize={10}
          onPageChange={(p) => setCurrentPage(p)}
          onSelectInstitution={(id) => setSelectedInstId(id)}
        />
      )}

      {/* 5. Deep Inspection Drilldown Modal */}
      <InstitutionDrilldownModal
        institutionId={selectedInstId}
        onClose={() => setSelectedInstId(null)}
      />
    </div>
  );
};
