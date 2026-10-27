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
  Sparkles,
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
    { to: "/demo-guide", label: "Demo Guide & Script", icon: Sparkles, requiredPerm: null, requiredRole: null },
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
    <aside className="w-64 border-r border-[#E5E5E5] bg-white flex flex-col justify-between p-4 hidden md:flex shrink-0 transition-colors">
      <div className="space-y-6">
        <div className="px-2 py-2">
          <h2 className="font-mono text-[11px] font-semibold text-black/50 uppercase tracking-[0.54px]">
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
                      "flex items-center gap-3 px-3.5 py-2 text-[14px] rounded-full transition-all tracking-[-0.1px]",
                      isActive
                        ? "bg-[#000000] text-white font-medium shadow-sm"
                        : "text-[#000000] hover:bg-[#F5F5F5] font-[340]"
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
          <div className="px-2 py-2 border-t border-[#E5E5E5]">
            <h2 className="font-mono text-[11px] font-semibold text-black/50 uppercase tracking-[0.54px] mb-2">
              Identity Scope
            </h2>
            <div className="bg-[#F5F5F5] p-3.5 rounded-[16px] border border-[#E5E5E5] text-xs space-y-1.5">
              <div className="flex items-center gap-1.5 text-black font-semibold">
                <Shield className="w-3.5 h-3.5 text-black" />
                <span>{user.roles.join(", ")}</span>
              </div>
              <div className="text-black font-medium truncate">{user.full_name}</div>
              <div className="font-mono text-[11px] text-black/60 truncate">{user.email}</div>
            </div>
          </div>
        )}
      </div>

      <div className="pt-4 border-t border-[#E5E5E5] px-2">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3.5 py-2 text-[14px] font-medium text-black hover:bg-rose-50 hover:text-rose-600 rounded-full transition-colors cursor-pointer"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
