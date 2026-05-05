import type { Metadata } from "next";

import { Footer } from "@/components/footer";
import { Nav } from "@/components/nav";

import "./globals.css";

export const metadata: Metadata = {
  title: "Compass Equity — Agentic equity research copilot",
  description:
    "Multi-agent LLM workflow for Taiwan-listed equity research. Grounded on TWSE, MOPS filings, and news with verifiable citations.",
  metadataBase: new URL("http://localhost:3000"),
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen flex flex-col">
        <Nav />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
