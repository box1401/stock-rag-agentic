"use client";

import { useState } from "react";
import { Loader2, Search } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTranslation } from "react-i18next";
import "@/lib/i18n";

import { analyze, type AnalyzeResponse } from "@/lib/api";
import { cn } from "@/lib/utils";
import { TraceTimeline } from "@/components/trace-timeline";

type Mode = "on_demand" | "daily" | "weekly";

export default function DashboardPage() {
  const { t, i18n } = useTranslation();
  const [ticker, setTicker] = useState("2330");
  const [mode, setMode] = useState<Mode>("on_demand");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  const lang = (i18n.resolvedLanguage?.startsWith("zh") ? "zh-TW" : "en") as
    | "zh-TW"
    | "en";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const data = await analyze({ ticker, mode, language: lang });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container py-10 space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">{t("dashboard_title")}</h1>
        <p className="text-muted-foreground">{t("subtagline")}</p>
      </header>

      <form
        onSubmit={onSubmit}
        className="flex flex-col gap-3 rounded-lg border bg-card p-4 md:flex-row md:items-end"
      >
        <div className="flex-1 space-y-1.5">
          <label className="text-sm font-medium">{t("input_ticker")}</label>
          <div className="flex items-center rounded-md border bg-background px-3 focus-within:ring-2 focus-within:ring-ring">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="flex-1 bg-transparent px-2 py-2 text-sm outline-none"
              placeholder="2330"
              maxLength={12}
              required
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">{t("mode_label")}</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as Mode)}
            className="rounded-md border bg-background px-3 py-2 text-sm"
          >
            <option value="on_demand">{t("mode_on_demand")}</option>
            <option value="daily">{t("mode_daily")}</option>
            <option value="weekly">{t("mode_weekly")}</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className={cn(
            "inline-flex items-center justify-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60",
          )}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {loading ? t("btn_loading") : t("btn_analyze")}
        </button>
      </form>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
          {error}
        </div>
      ) : null}

      {result ? <ReportView data={result} /> : null}
    </div>
  );
}

function ReportView({ data }: { data: AnalyzeResponse }) {
  const { t } = useTranslation();
  return (
    <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
      <article className="rounded-lg border bg-card p-6 prose prose-sm max-w-none dark:prose-invert">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.markdown}</ReactMarkdown>
      </article>
      <aside className="space-y-4">
        <div className="rounded-lg border bg-card p-4">
          <h3 className="text-sm font-semibold mb-3">{t("section_trace")}</h3>
          <TraceTimeline trace={data.trace} />
        </div>
      </aside>
    </section>
  );
}
