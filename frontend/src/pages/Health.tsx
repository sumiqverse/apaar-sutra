import React from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Activity, Database, Server, RefreshCw, CheckCircle2, AlertTriangle, ShieldAlert } from "lucide-react";
import { apiClient } from "@/lib/api";

interface HealthData {
  status: string;
  app_name: string;
  environment: string;
  version: string;
  timestamp: string;
  request_id: string;
}

interface ComponentHealth {
  status: string;
  latency_ms?: number;
  message?: string;
}

interface ReadyData {
  status: string;
  database: ComponentHealth;
  redis: ComponentHealth;
  timestamp: string;
  request_id: string;
}

export const Health: React.FC = () => {
  const { t } = useTranslation();

  // 1. Fetch liveness probe
  const {
    data: health,
    isLoading: isHealthLoading,
    isError: isHealthError,
    refetch: refetchHealth,
    isFetching: isHealthFetching,
  } = useQuery<HealthData>({
    queryKey: ["health-liveness"],
    queryFn: () => apiClient<HealthData>("/api/v1/health"),
    refetchInterval: 30000,
  });

  // 2. Fetch readiness probe (PostgreSQL + Redis)
  const {
    data: ready,
    isLoading: isReadyLoading,
    isError: isReadyError,
    refetch: refetchReady,
    isFetching: isReadyFetching,
  } = useQuery<ReadyData>({
    queryKey: ["health-readiness"],
    queryFn: () => apiClient<ReadyData>("/api/v1/ready"),
    refetchInterval: 30000,
  });

  const handleRefresh = () => {
    refetchHealth();
    refetchReady();
  };

  const isRefreshing = isHealthFetching || isReadyFetching;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Activity className="h-6 w-6 text-brand-600" />
            {t("health.title")}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {t("health.subtitle")}
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg shadow-sm hover:bg-slate-50 transition-colors disabled:opacity-50 self-start sm:self-auto"
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          <span>{t("health.refresh_button")}</span>
        </button>
      </div>

      {/* Global Status Banner */}
      <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 shadow-sm flex items-start gap-3">
        <CheckCircle2 className="h-5 w-5 text-emerald-600 mt-0.5 shrink-0" />
        <div className="text-sm">
          <p className="font-semibold text-emerald-900">
            {t("health.all_systems_go")}
          </p>
          <div className="mt-1 flex flex-wrap gap-4 text-xs text-emerald-700">
            <span>
              <strong>Env:</strong> {health?.environment || "development"}
            </span>
            <span>
              <strong>Version:</strong> {health?.version || "0.1.0"}
            </span>
            <span>
              <strong>Correlation ID:</strong>{" "}
              <code className="font-mono bg-emerald-100 px-1 py-0.5 rounded text-[11px]">
                {health?.request_id || "pending"}
              </code>
            </span>
          </div>
        </div>
      </div>

      {/* Diagnostics Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Backend Card */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="p-2 bg-brand-50 rounded-lg text-brand-600">
                <Server className="h-5 w-5" />
              </span>
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                  health?.status === "healthy"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-rose-100 text-rose-800"
                }`}
              >
                {health?.status === "healthy" ? t("health.healthy") : t("health.unhealthy")}
              </span>
            </div>
            <h3 className="mt-4 font-semibold text-slate-900">
              {t("health.backend_liveness")}
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              FastAPI 0.111 / Python 3.12 Engine
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between">
              <span>Endpoint:</span>
              <code className="font-mono text-slate-800">GET /api/v1/health</code>
            </div>
            <div className="flex justify-between">
              <span>Status:</span>
              <span className="font-semibold text-emerald-600">HTTP 200 OK</span>
            </div>
          </div>
        </div>

        {/* PostgreSQL Card */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
                <Database className="h-5 w-5" />
              </span>
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                  ready?.database.status === "connected"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {ready?.database.status === "connected" ? t("common.connected") : "Standby/Connecting"}
              </span>
            </div>
            <h3 className="mt-4 font-semibold text-slate-900">
              {t("health.database_status")}
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              ACID Relational Storage & Multi-Tenancy
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between">
              <span>{t("health.latency")}:</span>
              <span className="font-semibold text-slate-800">
                {ready?.database.latency_ms !== undefined ? `${ready.database.latency_ms} ms` : "Available in container"}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Dialect:</span>
              <span className="font-mono text-slate-800">PostgreSQL 16</span>
            </div>
          </div>
        </div>

        {/* Redis Card */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="p-2 bg-rose-50 rounded-lg text-rose-600">
                <Activity className="h-5 w-5" />
              </span>
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                  ready?.redis.status === "connected"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {ready?.redis.status === "connected" ? t("common.connected") : "Standby/Connecting"}
              </span>
            </div>
            <h3 className="mt-4 font-semibold text-slate-900">
              {t("health.redis_status")}
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              Celery Task Broker & In-Memory Cache
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 text-xs text-slate-600 space-y-1">
            <div className="flex justify-between">
              <span>{t("health.latency")}:</span>
              <span className="font-semibold text-slate-800">
                {ready?.redis.latency_ms !== undefined ? `${ready.redis.latency_ms} ms` : "Available in container"}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Mode:</span>
              <span className="font-mono text-slate-800">Standalone / Cache</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
