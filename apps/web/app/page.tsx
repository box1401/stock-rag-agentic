"use client";

import Link from "next/link";
import { ArrowRight, Layers, Network, ShieldCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import "@/lib/i18n";

export default function LandingPage() {
  const { t } = useTranslation();

  return (
    <div className="container py-16">
      <section className="flex flex-col items-center text-center gap-6 py-16">
        <span className="rounded-full border px-3 py-1 text-xs uppercase tracking-wider text-muted-foreground">
          M1 · agentic equity research
        </span>
        <h1 className="max-w-3xl text-4xl md:text-6xl font-semibold tracking-tight">
          {t("tagline")}
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground">{t("subtagline")}</p>
        <div className="flex gap-3 pt-2">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            {t("cta_dashboard")} <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="https://github.com/box1401/stock-rag-agentic#readme"
            className="inline-flex items-center gap-2 rounded-md border px-5 py-2.5 text-sm font-medium hover:bg-muted"
          >
            {t("cta_docs")}
          </a>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-3 pt-8">
        <Feature
          icon={<Network className="h-5 w-5" />}
          title={t("feature_multi_agent_title")}
          desc={t("feature_multi_agent_desc")}
        />
        <Feature
          icon={<Layers className="h-5 w-5" />}
          title={t("feature_rag_title")}
          desc={t("feature_rag_desc")}
        />
        <Feature
          icon={<ShieldCheck className="h-5 w-5" />}
          title={t("feature_audit_title")}
          desc={t("feature_audit_desc")}
        />
      </section>
    </div>
  );
}

function Feature({
  icon,
  title,
  desc,
}: {
  icon: React.ReactNode;
  title: string;
  desc: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted">
        {icon}
      </div>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{desc}</p>
    </div>
  );
}
