"use client";

import Link from "next/link";

import { CompassMark } from "@/components/compass-mark";
import { LanguageToggle } from "@/components/language-toggle";

export function Nav() {
  return (
    <header className="border-b">
      <div className="container flex h-14 items-center justify-between">
        <Link href="/" className="hover:opacity-80">
          <CompassMark />
        </Link>
        <nav className="flex items-center gap-3 text-sm">
          <Link href="/dashboard" className="hover:underline">
            Dashboard
          </Link>
          <Link href="/trace" className="hover:underline">
            Trace
          </Link>
          <a
            href="https://github.com/box1401/stock-rag-agentic"
            className="hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
          <LanguageToggle />
        </nav>
      </div>
    </header>
  );
}
