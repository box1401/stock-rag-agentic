"use client";

import { CircleDot } from "lucide-react";

import type { TraceEvent } from "@/lib/api";
import { cn } from "@/lib/utils";

const AGENT_COLOR: Record<TraceEvent["agent"], string> = {
  supervisor: "text-blue-600",
  data: "text-emerald-600",
  analyst: "text-violet-600",
  risk: "text-amber-600",
  reporter: "text-fuchsia-600",
};

export function TraceTimeline({ trace }: { trace: TraceEvent[] }) {
  if (!trace?.length) {
    return <p className="text-xs text-muted-foreground">No trace yet.</p>;
  }
  return (
    <ol className="space-y-3">
      {trace.map((evt, i) => (
        <li key={i} className="flex gap-2 text-xs">
          <CircleDot className={cn("mt-0.5 h-3 w-3 shrink-0", AGENT_COLOR[evt.agent])} />
          <div className="flex-1 leading-tight">
            <div className="font-medium">
              <span className={AGENT_COLOR[evt.agent]}>{evt.agent}</span> · {evt.event}
            </div>
            {evt.detail ? (
              <pre className="mt-1 max-h-24 overflow-auto rounded bg-muted p-1.5 text-[10px] text-muted-foreground">
                {JSON.stringify(evt.detail, null, 2)}
              </pre>
            ) : null}
            <time className="text-[10px] text-muted-foreground">
              {new Date(evt.timestamp).toLocaleTimeString()}
            </time>
          </div>
        </li>
      ))}
    </ol>
  );
}
