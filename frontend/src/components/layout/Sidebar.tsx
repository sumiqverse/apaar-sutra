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
    { to: "/", label: t("nav.dashboard"), icon: LayoutDashboard, requiredPerm: null },
    { to: "/students", label: t("nav.students"), icon: Users, requiredPerm: "students:read" },
    { to: "/verification", label: t("nav.verification"), icon: CheckCircle2, requiredPerm: null },
    { to: "/audit", label: "Audit Trail", icon: History, requiredPerm: "audit:read" },
    { to: "/health", label: t("nav.health"), icon: Activity, requiredPerm: null },
  ];

  // Filter items based on permissions
  const visibleNav = navItems.filter((item) => {
    if (!item.requiredPerm) return true;
    if (!user) return false;
    return user.permissions.includes(item.requiredPerm) || user.roles.includes("SUPER_ADMIN");
  });

  return (
    <aside className="w-64 border-r border-slate-200 bg-white flex flex-col justify-between p-4 hidden md:flex shrink-0">
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
                        ? "bg-indigo-50 text-indigo-700 font-semibold"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
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
          <div className="px-3 py-2 border-t border-slate-100">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Identity Scope
            </h2>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs space-y-1">
              <div className="flex items-center gap-1.5 text-indigo-700 font-bold">
                <Shield className="w-3.5 h-3.5" />
                <span>{user.roles.join(", ")}</span>
              </div>
              <div className="text-slate-700 truncate font-medium">{user.full_name}</div>
              <div className="text-slate-400 truncate text-[11px]">{user.email}</div>
            </div>
          </div>
        )}
      </div>

      <div className="pt-4 border-t border-slate-200">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 hover:text-red-700 rounded-lg transition-colors cursor-pointer"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
