"use client";

import { useTranslation } from "react-i18next";
import "@/lib/i18n";

export function Footer() {
  const { t } = useTranslation();
  return (
    <footer className="mt-16 border-t py-6 text-xs text-muted-foreground">
      <div className="container flex flex-col items-center gap-2 text-center md:flex-row md:justify-between">
        <span>© {new Date().getFullYear()} Compass Equity</span>
        <span>{t("footer_disclaimer")}</span>
      </div>
    </footer>
  );
}
