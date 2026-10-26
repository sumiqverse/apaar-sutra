import React from "react";
import { useTranslation } from "react-i18next";
import { Globe } from "lucide-react";

export const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const nextLang = i18n.language.startsWith("hi") ? "en" : "hi";
    i18n.changeLanguage(nextLang);
  };

  return (
    <button
      onClick={toggleLanguage}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-md shadow-sm hover:bg-slate-50 transition-colors"
      title="Switch Language / भाषा बदलें"
    >
      <Globe className="w-3.5 h-3.5 text-slate-500" />
      <span>{i18n.language.startsWith("hi") ? "English" : "हिंदी"}</span>
    </button>
  );
};
