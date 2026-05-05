"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Play, Square } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTranslation } from "react-i18next";
import "@/lib/i18n";

import { TraceTimeline } from "@/components/trace-timeline";
import type { TraceEvent } from "@/lib/api";
import { cn } from "@/lib/utils";

type StreamPhase = "idle" | "running" | "done" | "error";

interface FinalPayload {
  ticker: string;
  markdown: string;
  citations: Array<Record<string, unknown>>;
  indicators: Record<string, unknown> | null;
}

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function TraceStreamPage() {
  const { t, i18n } = useTranslation();
  const [ticker, setTicker] = useState("2330");
  const [phase, setPhase] = useState<StreamPhase>("idle");
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [final, setFinal] = useState<FinalPayload | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  function start() {
    stop();
    setEvents([]);
    setFinal(null);
    setErrorMsg(null);
    setPhase("running");

    const lang = i18n.resolvedLanguage?.startsWith("zh") ? "zh-TW" : "en";
    const url = `${BASE}/api/v1/analyze/stream?ticker=${encodeURIComponent(
      ticker,
    )}&mode=on_demand&language=${lang}`;
    const es = new EventSource(url);
    sourceRef.current = es;

    es.addEventListener("trace", (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data) as TraceEvent;
        setEvents((prev) => [...prev, data]);
      } catch {}
    });
    es.addEventListener("final", (e) => {
      try {
        setFinal(JSON.parse((e as MessageEvent).data) as FinalPayload);
      } catch {}
    });
    es.addEventListener("error", (e) => {
      const ev = e as MessageEvent;
      try {
        const parsed = JSON.parse(ev.data ?? "{}");
        setErrorMsg(parsed.message || "stream error");
      } catch {
        setErrorMsg("connection lost");
      }
      setPhase("error");
      es.close();
      sourceRef.current = null;
    });
    es.addEventListener("done", () => {
      setPhase("done");
      es.close();
      sourceRef.current = null;
    });
  }

  function stop() {
    sourceRef.current?.close();
    sourceRef.current = null;
    if (phase === "running") setPhase("idle");
  }

  useEffect(() => () => sourceRef.current?.close(), []);

  return (
    <div className="container py-10 space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">
          {t("section_trace")} (live)
        </h1>
        <p className="text-muted-foreground">
          Server-sent agent trace — every node update is pushed in real time.
        </p>
      </header>

      <div className="flex items-center gap-3 rounded-lg border bg-card p-4">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          className="flex-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          placeholder="2330"
          disabled={phase === "running"}
          maxLength={12}
        />
        {phase === "running" ? (
          <button
            onClick={stop}
            className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted"
          >
            <Square className="h-4 w-4" /> Stop
          </button>
        ) : (
          <button
            onClick={start}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            <Play className="h-4 w-4" /> Start
          </button>
        )}
      </div>

      {errorMsg ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
          {errorMsg}
        </div>
      ) : null}

      <section className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-lg border bg-card p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            {phase === "running" ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {t("section_trace")} ({events.length})
          </h3>
          <TraceTimeline trace={events} />
        </div>

        <div className="rounded-lg border bg-card p-4">
          <h3 className="mb-3 text-sm font-semibold">
            {final ? t("section_summary") : "Waiting for report…"}
          </h3>
          {final ? (
            <article className={cn("prose prose-sm max-w-none dark:prose-invert")}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{final.markdown}</ReactMarkdown>
            </article>
          ) : (
            <p className="text-xs text-muted-foreground">No report yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}
