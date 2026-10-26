import React, { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  LayoutDashboard,
  Users,
  CheckCircle2,
  Activity,
  History,
  LogOut,
  Shield,
  UploadCloud,
  Building,
  ShieldCheck,
  FileCheck2,
  FileText,
  Sliders,
  Code,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient, clearAuthTokens } from "@/lib/api";

interface UserMe {
  roles: string[];
  permissions: string[];
  full_name: string;
  email: string;
}

export const Sidebar: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [user, setUser] = useState<UserMe | null>(null);

  useEffect(() => {
    apiClient<UserMe>("/api/v1/auth/me")
      .then(setUser)
      .catch(() => {});
  }, []);

  const handleLogout = async () => {
    try {
      await apiClient("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // Ignore network errors during logout
    } finally {
      clearAuthTokens();
      navigate("/login");
    }
  };

  const navItems = [
    { to: "/", label: "AICTE Dashboard", icon: LayoutDashboard, requiredPerm: null, requiredRole: null },
    { to: "/institution-dashboard", label: "Institution Portal", icon: Building, requiredPerm: null, requiredRole: null },
    { to: "/reports", label: "Statutory Reports", icon: FileText, requiredPerm: null, requiredRole: null },
    { to: "/admin", label: "Admin Console", icon: Sliders, requiredPerm: null, requiredRole: "SUPER_ADMIN" },
    { to: "/developers", label: "Developer Docs", icon: Code, requiredPerm: null, requiredRole: null },
    { to: "/verifier", label: "Verifier Portal (DPDP)", icon: CheckCircle2, requiredPerm: null, requiredRole: null },
    { to: "/student/consent", label: "Student Privacy (DPDP)", icon: ShieldCheck, requiredPerm: null, requiredRole: null },
    { to: "/tamper-demo", label: "Tamper Proof Demo", icon: FileCheck2, requiredPerm: null, requiredRole: null },
    { to: "/ingestion", label: t("nav.ingestion") || "Student Ingestion", icon: UploadCloud, requiredPerm: null, requiredRole: null },
    { to: "/audit", label: "Audit Trail", icon: History, requiredPerm: "audit:read", requiredRole: null },
    { to: "/health", label: t("nav.health") || "System Health", icon: Activity, requiredPerm: null, requiredRole: null },
  ];

  // Filter items based on permissions
  const visibleNav = navItems.filter((item) => {
    if (item.requiredRole && (!user || !user.roles.includes(item.requiredRole))) return false;
    if (!item.requiredPerm) return true;
    if (!user) return false;
    return user.permissions.includes(item.requiredPerm) || user.roles.includes("SUPER_ADMIN");
  });

  return (
    <aside className="w-64 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between p-4 hidden md:flex shrink-0 transition-colors">
      <div className="space-y-6">
        <div className="px-3 py-2">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Navigation
          </h2>
          <nav className="mt-3 space-y-1">
            {visibleNav.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                      isActive
                        ? "bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-semibold"
                        : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white"
                    )
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {user && (
          <div className="px-3 py-2 border-t border-slate-100 dark:border-slate-800">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Identity Scope
            </h2>
            <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg border border-slate-200 dark:border-slate-700 text-xs space-y-1">
              <div className="flex items-center gap-1.5 text-indigo-700 dark:text-indigo-400 font-bold">
                <Shield className="w-3.5 h-3.5" />
                <span>{user.roles.join(", ")}</span>
              </div>
              <div className="text-slate-700 dark:text-slate-200 truncate font-medium">{user.full_name}</div>
              <div className="text-slate-400 truncate text-[11px]">{user.email}</div>
            </div>
          </div>
        )}
      </div>

      <div className="pt-4 border-t border-slate-200 dark:border-slate-800">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 hover:text-red-700 rounded-lg transition-colors cursor-pointer"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
