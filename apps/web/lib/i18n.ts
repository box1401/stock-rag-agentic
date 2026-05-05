"use client";

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import zh from "@/i18n/zh-TW.json";
import en from "@/i18n/en.json";

if (!i18n.isInitialized) {
  i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      resources: { "zh-TW": { translation: zh }, en: { translation: en } },
      fallbackLng: "en",
      interpolation: { escapeValue: false },
      detection: { order: ["localStorage", "navigator"], caches: ["localStorage"] },
    });
}

export default i18n;
