/**
 * Root Layout — Phase 5B.3 (Frontend Project Setup)
 *
 * • Defines full-page SEO metadata (5B.3, 5B.6 — Lighthouse audit)
 * • Loads Google Fonts (Inter via Geist) with display=swap
 * • Wraps app in next-themes ThemeProvider (5B.6.4)
 * • suppressHydrationWarning prevents SSR/CSR mismatch on class="dark"
 */

import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { AuthProvider } from "@/components/AuthProvider";

// ── Fonts (display=swap for performance — 5B.6.6 Lighthouse) ──────────────
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

// ── SEO Metadata (5B.3, 5B.6.6 — Lighthouse accessibility) ──────────────────
export const metadata: Metadata = {
  title: {
    default: "SecureHall-RAG — Citation-Backed Document Q&A",
    template: "%s | SecureHall-RAG",
  },
  description:
    "Upload documents and ask questions — receive verifiable answers with inline citations, "
    + "confidence scores, and hallucination detection powered by SecureHall-RAG.",
  keywords: [
    "RAG",
    "Retrieval Augmented Generation",
    "document QA",
    "citations",
    "hallucination detection",
    "AI",
    "SecureHall",
  ],
  authors: [{ name: "SecureHall-RAG Team" }],
  creator: "SecureHall-RAG",
  robots: {
    index: false,  // Private research tool — do not index
    follow: false,
  },
  // Open Graph
  openGraph: {
    type: "website",
    title: "SecureHall-RAG",
    description:
      "Citation-backed document question-answering with hallucination detection.",
    siteName: "SecureHall-RAG",
  },
};

// ── Viewport / theme colour (5B.6.1 — mobile) ───────────────────────────────
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,   // Allow pinch-to-zoom (accessibility)
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#1a1a1a" },
  ],
};

// ── Root layout component ─────────────────────────────────────────────────────
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      {/*
       * suppressHydrationWarning on <body> is intentional:
       * next-themes injects class="dark" after hydration and
       * this prevents React from logging a mismatch warning.
       */}
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem={true}
          disableTransitionOnChange={false}
        >
          <AuthProvider>
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
