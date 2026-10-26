import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enTranslation from "../public/locales/en/translation.json";
import hiTranslation from "../public/locales/hi/translation.json";

const resources = {
  en: {
    translation: enTranslation,
  },
  hi: {
    translation: hiTranslation,
  },
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: "en",
    fallbackLng: "en",
    interpolation: {
      escapeValue: false, // React already escapes values
    },
  });

export default i18n;
