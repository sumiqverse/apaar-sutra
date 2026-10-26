import React from "react";
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  LayoutDashboard,
  Users,
  CheckCircle2,
  Activity,
  BarChart3,
  FileCode2,
} from "lucide-react";
import { cn } from "@/lib/utils";

export const Sidebar: React.FC = () => {
  const { t } = useTranslation();

  const navItems = [
    { to: "/", label: t("nav.dashboard"), icon: LayoutDashboard },
    { to: "/students", label: t("nav.students"), icon: Users },
    { to: "/verification", label: t("nav.verification"), icon: CheckCircle2 },
    { to: "/health", label: t("nav.health"), icon: Activity },
  ];

  return (
    <aside className="w-64 border-r border-slate-200 bg-white flex flex-col justify-between p-4 hidden md:flex shrink-0">
      <div className="space-y-6">
        <div className="px-3 py-2">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Navigation
          </h2>
          <nav className="mt-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                      isActive
                        ? "bg-brand-50 text-brand-700 font-semibold"
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

        <div className="px-3 py-2">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Specifications
          </h2>
          <div className="mt-3 space-y-2 text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div>
              <span className="font-semibold text-slate-700">Problem ID:</span> 26263
            </div>
            <div>
              <span className="font-semibold text-slate-700">Protocol:</span> APAAR v1.0
            </div>
            <div>
              <span className="font-semibold text-slate-700">Encryption:</span> SHA-256 + HMAC
            </div>
          </div>
        </div>
      </div>

      <div className="border-t border-slate-200 pt-3 px-3">
        <div className="text-[11px] text-slate-400">
          AICTE Central Platform &copy; 2026
        </div>
      </div>
    </aside>
  );
};
