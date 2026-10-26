import React from "react";
import { useTranslation } from "react-i18next";
import { ShieldCheck, ExternalLink } from "lucide-react";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

export const Navbar: React.FC = () => {
  const { t } = useTranslation();

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 px-6 backdrop-blur shadow-sm transition-colors">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-brand-600 to-indigo-800 text-white shadow-md">
          <ShieldCheck className="h-6 w-6" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
              {t("app.title")}
            </span>
            <span className="rounded bg-brand-100 dark:bg-brand-950 px-1.5 py-0.5 text-[10px] font-semibold text-brand-800 dark:text-brand-300 uppercase tracking-wider">
              AICTE Core
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-medium hidden sm:block">
            {t("app.subtitle")}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        <ThemeToggle />

        <div className="h-4 w-px bg-slate-200 dark:bg-slate-800" />

        <LanguageSwitcher />

        <div className="h-4 w-px bg-slate-200 dark:bg-slate-800 hidden sm:block" />

        <a
          href="/api/docs"
          target="_blank"
          rel="noreferrer"
          className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors"
        >
          <span>{t("nav.docs")}</span>
          <ExternalLink className="h-3 w-3" />
        </a>

        <div className="flex items-center gap-2 pl-2">
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400 hidden md:inline">
            SIH 26263 Online
          </span>
        </div>
      </div>
    </header>
  );
};
