import React, { useEffect, useState } from "react";
import {
  ShieldAlert,
  Sliders,
  Building2,
  Users,
  Key,
  Radio,
  Activity,
  Plus,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  RotateCw,
  Trash2,
  Save,
  Check,
  Copy,
  Search,
  ExternalLink,
  ChevronRight,
  Database,
  Cpu,
  Inbox,
  Clock,
  Send,
} from "lucide-react";
import { apiClient } from "@/lib/api";

export const AdminConsole: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    "rules" | "institutions" | "users" | "clients" | "webhooks" | "telemetry"
  >("rules");
  const [loading, setLoading] = useState<boolean>(true);

  // 1. Rules State
  const [rules, setRules] = useState<any[]>([]);
  const [savingRule, setSavingRule] = useState<string | null>(null);

  // 2. Institutions State
  const [institutions, setInstitutions] = useState<any[]>([]);
  const [showAddInstModal, setShowAddInstModal] = useState<boolean>(false);
  const [newInst, setNewInst] = useState({
    aicte_id: "",
    name: "",
    state: "Maharashtra",
    district: "",
    sanctioned_intake: 300,
  });

  // 3. Users State
  const [users, setUsers] = useState<any[]>([]);

  // 4. API Clients State
  const [apiClients, setApiClients] = useState<any[]>([]);
  const [showNewClientModal, setShowNewClientModal] = useState<boolean>(false);
  const [newClientName, setNewClientName] = useState<string>("");
  const [rotatedSecretModal, setRotatedSecretModal] = useState<{
    clientId: string;
    keyId: string;
    secret: string;
  } | null>(null);

  // 5. Webhooks State
  const [webhookSubs, setWebhookSubs] = useState<any[]>([]);
  const [deliveryLogs, setDeliveryLogs] = useState<any[]>([]);
  const [showNewSubModal, setShowNewSubModal] = useState<boolean>(false);
  const [newWebhook, setNewWebhook] = useState({
    url: "https://",
    events: ["batch.completed", "alert.created"],
  });

  // 6. Telemetry & Policy State
  const [telemetry, setTelemetry] = useState<any>(null);
  const [policies, setPolicies] = useState<any[]>([]);

  useEffect(() => {
    loadTabData(activeTab);
  }, [activeTab]);

  const loadTabData = async (tab: string) => {
    setLoading(true);
    try {
      if (tab === "rules") {
        const res = await apiClient<any[]>("/api/v1/admin/rules");
        setRules(res);
      } else if (tab === "institutions") {
        const res = await apiClient<any[]>("/api/v1/admin/institutions");
        setInstitutions(res);
      } else if (tab === "users") {
        const res = await apiClient<any[]>("/api/v1/admin/users");
        setUsers(res);
      } else if (tab === "clients") {
        const res = await apiClient<any[]>("/api/v1/admin/api-clients");
        setApiClients(res);
      } else if (tab === "webhooks") {
        const [subs, logs] = await Promise.all([
          apiClient<any[]>("/api/v1/admin/webhooks/subscriptions"),
          apiClient<any[]>("/api/v1/admin/webhooks/deliveries"),
        ]);
        setWebhookSubs(subs);
        setDeliveryLogs(logs);
      } else if (tab === "telemetry") {
        const [tel, pol] = await Promise.all([
          apiClient<any>("/api/v1/admin/telemetry"),
          apiClient<any[]>("/api/v1/admin/policies"),
        ]);
        setTelemetry(tel);
        setPolicies(pol);
      }
    } catch (err: any) {
      console.error("Failed to load admin tab data:", err);
    } finally {
      setLoading(false);
    }
  };

  // Rule Update
  const handleSaveRule = async (rule: any) => {
    setSavingRule(rule.code);
    try {
      await apiClient(`/api/v1/admin/rules/${rule.code}`, {
        method: "PUT",
        body: JSON.stringify({
          is_active: rule.is_active,
          severity: rule.severity,
          parameters: rule.parameters,
        }),
      });
      alert(`Rule ${rule.code} updated successfully.`);
    } catch (err: any) {
      alert("Failed to update rule: " + err.message);
    } finally {
      setSavingRule(null);
    }
  };

  // Institution Add
  const handleCreateInstitution = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient("/api/v1/admin/institutions", {
        method: "POST",
        body: JSON.stringify(newInst),
      });
      setShowAddInstModal(false);
      setNewInst({ aicte_id: "", name: "", state: "Maharashtra", district: "", sanctioned_intake: 300 });
      loadTabData("institutions");
    } catch (err: any) {
      alert("Failed to create institution: " + err.message);
    }
  };

  // Create API Client
  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await apiClient<any>("/api/v1/admin/api-clients", {
        method: "POST",
        body: JSON.stringify({
          name: newClientName,
          scopes: ["students:write", "batches:upload"],
        }),
      });
      setShowNewClientModal(false);
      setNewClientName("");
      setRotatedSecretModal({
        clientId: res.client_id,
        keyId: res.key_id,
        secret: res.secret,
      });
      loadTabData("clients");
    } catch (err: any) {
      alert("Failed to register client: " + err.message);
    }
  };

  // Rotate Secret
  const handleRotateSecret = async (clientId: string) => {
    if (!window.confirm("Are you sure? Rotating the secret will invalidate the existing secret immediately.")) {
      return;
    }
    try {
      const res = await apiClient<any>(`/api/v1/admin/api-clients/${clientId}/rotate-secret`, {
        method: "POST",
      });
      setRotatedSecretModal({
        clientId: res.client_id,
        keyId: res.key_id,
        secret: res.secret,
      });
      loadTabData("clients");
    } catch (err: any) {
      alert("Failed to rotate secret: " + err.message);
    }
  };

  // Revoke Client
  const handleRevokeClient = async (clientId: string) => {
    if (!window.confirm("Revoke this API client? External ERP calls using these credentials will be rejected.")) {
      return;
    }
    try {
      await apiClient(`/api/v1/admin/api-clients/${clientId}`, {
        method: "DELETE",
      });
      loadTabData("clients");
    } catch (err: any) {
      alert("Failed to revoke client: " + err.message);
    }
  };

  // Create Webhook Sub
  const handleCreateWebhookSub = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient("/api/v1/admin/webhooks/subscriptions", {
        method: "POST",
        body: JSON.stringify(newWebhook),
      });
      setShowNewSubModal(false);
      loadTabData("webhooks");
    } catch (err: any) {
      alert("Failed to create webhook subscription: " + err.message);
    }
  };

  // Retry Webhook Delivery
  const handleRetryDelivery = async (deliveryId: string) => {
    try {
      await apiClient(`/api/v1/admin/webhooks/deliveries/${deliveryId}/retry`, {
        method: "POST",
      });
      alert("Webhook delivery dispatched for retry.");
      loadTabData("webhooks");
    } catch (err: any) {
      alert("Failed to retry delivery: " + err.message);
    }
  };

  // Toggle Policy
  const handleSavePolicy = async (key: string, value: any) => {
    try {
      await apiClient("/api/v1/admin/policies", {
        method: "POST",
        body: JSON.stringify({ key, value }),
      });
      loadTabData("telemetry");
    } catch (err: any) {
      alert("Failed to update policy: " + err.message);
    }
  };

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-rose-600/10 text-rose-600 dark:text-rose-400 rounded-xl">
              <ShieldAlert className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                  Super Admin Control Console
                </h1>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 uppercase tracking-wider">
                  Super Admin Role Required
                </span>
              </div>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Rule thresholds, institutional registry, user RBAC, API secrets, webhooks & real-time telemetry.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={() => loadTabData(activeTab)}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Workspace
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 space-x-6 text-sm font-medium overflow-x-auto pb-1">
        <button
          onClick={() => setActiveTab("rules")}
          className={`pb-3 transition flex items-center gap-2 border-b-2 shrink-0 ${
            activeTab === "rules"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <Sliders className="w-4 h-4" />
          Validation Rules Engine
        </button>
        <button
          onClick={() => setActiveTab("institutions")}
          className={`pb-3 transition flex items-center gap-2 border-b-2 shrink-0 ${
            activeTab === "institutions"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <Building2 className="w-4 h-4" />
          Institutions Governance
        </button>
        <button
          onClick={() => setActiveTab("users")}
          className={`pb-3 transition flex items-center gap-2 border-b-2 shrink-0 ${
            activeTab === "users"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <Users className="w-4 h-4" />
          Users & RBAC
        </button>
        <button
          onClick={() => setActiveTab("clients")}
          className={`pb-3 transition flex items-center gap-2 border-b-2 shrink-0 ${
            activeTab === "clients"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <Key className="w-4 h-4" />
          API Clients & HMAC Secrets
        </button>
        <button
          onClick={() => setActiveTab("webhooks")}
          className={`pb-3 transition flex items-center gap-2 border-b-2 shrink-0 ${
            activeTab === "webhooks"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <Radio className="w-4 h-4" />
          Webhooks & DLQ
        </button>
        <button
          onClick={() => setActiveTab("telemetry")}
          className={`pb-3 transition flex items-center gap-2 border-b-2 shrink-0 ${
            activeTab === "telemetry"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 font-semibold"
              : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <Activity className="w-4 h-4" />
          System Telemetry & Policies
        </button>
      </div>

      {/* WORKSPACE 1: RULES ENGINE */}
      {activeTab === "rules" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Statutory Validation Rules
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Configure threshold parameters, severity classifications, and active states.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {rules.map((rule, idx) => (
              <div
                key={rule.code}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-4"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400">
                      {rule.code}
                    </span>
                    <h3 className="font-semibold text-slate-900 dark:text-white text-sm mt-0.5">
                      {rule.name}
                    </h3>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rule.is_active}
                      onChange={(e) => {
                        const updated = [...rules];
                        updated[idx].is_active = e.target.checked;
                        setRules(updated);
                      }}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>

                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  {rule.description}
                </p>

                <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-slate-400">Severity:</span>
                    <select
                      value={rule.severity}
                      onChange={(e) => {
                        const updated = [...rules];
                        updated[idx].severity = e.target.value;
                        setRules(updated);
                      }}
                      className="text-xs font-semibold px-2 py-1 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 focus:outline-none"
                    >
                      <option value="CRITICAL">CRITICAL</option>
                      <option value="WARNING">WARNING</option>
                      <option value="INFO">INFO</option>
                    </select>
                  </div>

                  <button
                    onClick={() => handleSaveRule(rule)}
                    disabled={savingRule === rule.code}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-indigo-600 dark:bg-slate-800 dark:hover:bg-indigo-600 text-white text-xs font-semibold rounded-lg transition"
                  >
                    <Save className="w-3.5 h-3.5" />
                    Save Rule
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* WORKSPACE 2: INSTITUTIONS */}
      {activeTab === "institutions" && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Institutions Directory
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Regulated colleges and approved annual student intake quotas.
              </p>
            </div>
            <button
              onClick={() => setShowAddInstModal(true)}
              className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl transition shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Register Institution
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/60 uppercase font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4">AICTE ID</th>
                  <th className="py-3 px-4">Institution Name</th>
                  <th className="py-3 px-4">State & Region</th>
                  <th className="py-3 px-4">Sanctioned Intake</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {institutions.map((inst) => (
                  <tr key={inst.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 font-mono font-bold text-indigo-600 dark:text-indigo-400">
                      {inst.aicte_id}
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-900 dark:text-white">
                      {inst.name}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 dark:text-slate-400">
                      {inst.state} {inst.district ? `(${inst.district})` : ""}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold">
                      {inst.sanctioned_intake?.toLocaleString() || "N/A"}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                        {inst.status || "ACTIVE"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* WORKSPACE 3: USERS & RBAC */}
      {activeTab === "users" && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              User Accounts & Role Permissions
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Manage platform administrators, regional AICTE regulators, and institutional nodal officers.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/60 uppercase font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4">Full Name</th>
                  <th className="py-3 px-4">Email</th>
                  <th className="py-3 px-4">Assigned Role</th>
                  <th className="py-3 px-4">MFA Enrolled</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 font-medium text-slate-900 dark:text-white">
                      {u.full_name}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 dark:text-slate-400 font-mono">
                      {u.email}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        u.role === "SUPER_ADMIN"
                          ? "bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300"
                          : u.role === "REGULATOR"
                          ? "bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300"
                          : "bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300"
                      }`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {u.mfa_enabled ? (
                        <span className="text-emerald-500 font-semibold flex items-center gap-1">
                          <CheckCircle className="w-3.5 h-3.5" /> Enrolled
                        </span>
                      ) : (
                        <span className="text-slate-400">Disabled</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                        {u.is_active ? "ACTIVE" : "SUSPENDED"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* WORKSPACE 4: API CLIENTS */}
      {activeTab === "clients" && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                ERP API Clients & Key Management
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                System-to-system HMAC credentials for campus management systems and automated pipelines.
              </p>
            </div>
            <button
              onClick={() => setShowNewClientModal(true)}
              className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl transition shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Register API Client
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/60 uppercase font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-3 px-4">Client Name</th>
                  <th className="py-3 px-4">Key ID (Public)</th>
                  <th className="py-3 px-4">Scopes</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {apiClients.map((c) => (
                  <tr key={c.client_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">
                      {c.name}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-indigo-600 dark:text-indigo-400">
                      {c.key_id}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex gap-1 flex-wrap">
                        {c.scopes.map((s: string) => (
                          <span key={s} className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono">
                            {s}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => handleRotateSecret(c.client_id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-slate-100 hover:bg-amber-50 dark:bg-slate-800 dark:hover:bg-amber-950 text-slate-700 hover:text-amber-600 dark:text-slate-300 rounded-lg text-xs font-semibold transition"
                      >
                        <RotateCw className="w-3.5 h-3.5" />
                        Rotate Secret
                      </button>
                      <button
                        onClick={() => handleRevokeClient(c.client_id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-slate-100 hover:bg-rose-50 dark:bg-slate-800 dark:hover:bg-rose-950 text-slate-700 hover:text-rose-600 dark:text-slate-300 rounded-lg text-xs font-semibold transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* WORKSPACE 5: WEBHOOKS & DLQ */}
      {activeTab === "webhooks" && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                  Active Webhook Subscriptions
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Real-time event notification endpoints signed with HMAC-SHA256 (X-Signature).
                </p>
              </div>
              <button
                onClick={() => setShowNewSubModal(true)}
                className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl transition shadow-sm"
              >
                <Plus className="w-4 h-4" />
                New Subscription
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {webhookSubs.map((sub) => (
                <div key={sub.id} className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold text-slate-900 dark:text-white truncate max-w-[280px]">
                      {sub.url}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                      ACTIVE
                    </span>
                  </div>
                  <div className="flex gap-1 flex-wrap">
                    {sub.events.map((ev: string) => (
                      <span key={ev} className="px-1.5 py-0.5 rounded text-[10px] bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 font-mono border border-slate-200 dark:border-slate-800">
                        {ev}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Delivery Logs & Dead-Letter Queue (DLQ) */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Delivery Logs & Dead-Letter Queue (DLQ)
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Inspect failed dispatches after 5 exponential backoff retries and trigger manual replays.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
                <thead className="bg-slate-50 dark:bg-slate-800/60 uppercase font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Event Type</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Attempts</th>
                    <th className="py-3 px-4">HTTP Status</th>
                    <th className="py-3 px-4">Next Retry / Timestamp</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {deliveryLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                      <td className="py-3.5 px-4 font-mono font-semibold text-indigo-600 dark:text-indigo-400">
                        {log.event_type}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          log.status === "SUCCESS"
                            ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300"
                            : log.status === "RETRYING"
                            ? "bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300"
                            : "bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300"
                        }`}>
                          {log.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-medium">
                        {log.attempt_count} / 5
                      </td>
                      <td className="py-3.5 px-4 font-mono">
                        {log.status_code || "N/A"}
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">
                        {log.next_retry_at
                          ? `Next: ${new Date(log.next_retry_at).toLocaleTimeString()}`
                          : new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => handleRetryDelivery(log.id)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-slate-100 hover:bg-indigo-50 dark:bg-slate-800 dark:hover:bg-indigo-950 text-slate-700 hover:text-indigo-600 dark:text-slate-300 rounded-lg text-xs font-semibold transition"
                        >
                          <Send className="w-3.5 h-3.5" />
                          Retry Dispatch
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* WORKSPACE 6: TELEMETRY & POLICY */}
      {activeTab === "telemetry" && (
        <div className="space-y-6">
          {telemetry && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-slate-400 text-xs font-medium">
                  <Inbox className="w-4 h-4 text-indigo-500" />
                  Queue Depth
                </div>
                <div className="text-xl font-bold text-slate-900 dark:text-white mt-2">
                  {telemetry.queue_depth} jobs
                </div>
              </div>
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-slate-400 text-xs font-medium">
                  <AlertTriangle className="w-4 h-4 text-rose-500" />
                  Failed Jobs
                </div>
                <div className="text-xl font-bold text-rose-600 dark:text-rose-400 mt-2">
                  {telemetry.failed_jobs}
                </div>
              </div>
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-slate-400 text-xs font-medium">
                  <Clock className="w-4 h-4 text-emerald-500" />
                  Nightly Scan
                </div>
                <div className="text-sm font-semibold text-slate-900 dark:text-white mt-2 truncate">
                  {new Date(telemetry.last_nightly_scan).toLocaleDateString()}
                </div>
              </div>
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-slate-400 text-xs font-medium">
                  <Database className="w-4 h-4 text-blue-500" />
                  DB Size (Est.)
                </div>
                <div className="text-xl font-bold text-slate-900 dark:text-white mt-2">
                  {telemetry.db_size_mb} MB
                </div>
              </div>
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-slate-400 text-xs font-medium">
                  <Cpu className="w-4 h-4 text-purple-500" />
                  ML Anomaly Model
                </div>
                <div className="text-sm font-bold text-slate-900 dark:text-white mt-2 truncate font-mono">
                  {telemetry.ml_model_version}
                </div>
              </div>
            </div>
          )}

          {/* Policy Settings */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Statutory Quota & Intake Policy Settings
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Configure which student admission quotas count towards the sanctioned intake threshold.
              </p>
            </div>

            <div className="space-y-3 max-w-2xl">
              {policies.map((p) => (
                <div key={p.key} className="flex items-center justify-between p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                  <div>
                    <div className="font-semibold text-xs text-slate-900 dark:text-white">
                      {p.key.replace(/_/g, " ").toUpperCase()}
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                      {p.description || "System policy parameter controlling intake calculation"}
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={Boolean(p.value)}
                      onChange={(e) => handleSavePolicy(p.key, e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Modal: Secret Display After Creation / Rotation */}
      {rotatedSecretModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-amber-500 font-semibold text-sm">
              <Key className="w-5 h-5" />
              API Secret Generated
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Please copy this secret immediately. For security, it cannot be displayed again.
            </p>
            <div className="p-3 bg-slate-950 text-amber-400 rounded-xl font-mono text-xs break-all">
              {rotatedSecretModal.secret}
            </div>
            <button
              onClick={() => {
                navigator.clipboard.writeText(rotatedSecretModal.secret);
                setRotatedSecretModal(null);
                alert("Secret copied to clipboard.");
              }}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl transition"
            >
              Copy Secret & Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Modal: Add Institution */}
      {showAddInstModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <form onSubmit={handleCreateInstitution} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="font-bold text-slate-900 dark:text-white text-base">Register New Institution</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">AICTE ID</label>
                <input
                  required
                  placeholder="e.g. 1-9876543210"
                  value={newInst.aicte_id}
                  onChange={(e) => setNewInst({ ...newInst, aicte_id: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Institution Full Name</label>
                <input
                  required
                  placeholder="e.g. Pune Institute of Computer Technology"
                  value={newInst.name}
                  onChange={(e) => setNewInst({ ...newInst, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">State</label>
                  <input
                    required
                    value={newInst.state}
                    onChange={(e) => setNewInst({ ...newInst, state: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Sanctioned Intake</label>
                  <input
                    type="number"
                    required
                    value={newInst.sanctioned_intake}
                    onChange={(e) => setNewInst({ ...newInst, sanctioned_intake: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white"
                  />
                </div>
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowAddInstModal(false)}
                className="flex-1 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-semibold rounded-xl"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl"
              >
                Create
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modal: Add API Client */}
      {showNewClientModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <form onSubmit={handleCreateClient} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="font-bold text-slate-900 dark:text-white text-base">Register External ERP Client</h3>
            <div className="text-xs space-y-2">
              <label className="text-slate-400 block">Client / System Name</label>
              <input
                required
                placeholder="e.g. Campus SAP ERP Connector"
                value={newClientName}
                onChange={(e) => setNewClientName(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowNewClientModal(false)}
                className="flex-1 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-semibold rounded-xl"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl"
              >
                Generate Credentials
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modal: Add Webhook */}
      {showNewSubModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <form onSubmit={handleCreateWebhookSub} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="font-bold text-slate-900 dark:text-white text-base">New Webhook Subscription</h3>
            <div className="text-xs space-y-3">
              <div>
                <label className="text-slate-400 block mb-1">Target Endpoint URL</label>
                <input
                  required
                  placeholder="https://college.edu/webhooks/apaar"
                  value={newWebhook.url}
                  onChange={(e) => setNewWebhook({ ...newWebhook, url: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white"
                />
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowNewSubModal(false)}
                className="flex-1 py-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-semibold rounded-xl"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl"
              >
                Subscribe
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
export default AdminConsole;
