"use client";

import { useTranslation } from "react-i18next";
import "@/lib/i18n";

import { cn } from "@/lib/utils";

export function LanguageToggle({ className }: { className?: string }) {
  const { i18n, t } = useTranslation();
  const current = i18n.resolvedLanguage ?? "en";
  const next = current.startsWith("zh") ? "en" : "zh-TW";
  return (
    <button
      onClick={() => i18n.changeLanguage(next)}
      className={cn(
        "rounded-md border px-3 py-1 text-sm font-medium hover:bg-muted transition",
        className,
      )}
      aria-label={t("lang_label")}
    >
      {current.startsWith("zh") ? "EN" : "繁"}
    </button>
  );
}
