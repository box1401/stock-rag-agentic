import { cn } from "@/lib/utils";

export function CompassMark({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <svg
        width="28"
        height="28"
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden
      >
        <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="2" />
        <path
          d="M16 4 L20 16 L16 28 L12 16 Z"
          fill="currentColor"
          opacity="0.85"
        />
        <circle cx="16" cy="16" r="2" fill="hsl(var(--background))" />
      </svg>
      <span className="text-lg font-semibold tracking-tight">Compass Equity</span>
    </div>
  );
}
