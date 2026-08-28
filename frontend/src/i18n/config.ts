import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import { en } from "./en";
import { it } from "./it";

void i18n.use(LanguageDetector).use(initReactI18next).init({
  resources: { en: { translation: en }, it: { translation: it } },
  fallbackLng: "en",
  supportedLngs: ["en", "it"],
  interpolation: { escapeValue: false },
  detection: {
    order: ["localStorage", "navigator"],
    caches: ["localStorage"],
  },
});

export default i18n;
