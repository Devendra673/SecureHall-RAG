"use client";

/**
 * Home Page — Phase 5B.3 (Frontend Project Setup) / 5B.4 (Core UI)
 *
 * Assembles the full-screen portal layout:
 *   Header (top bar) + Sidebar (left) + ChatInterface (main) + Toaster
 *
 * SEO metadata is defined in layout.tsx (server component).
 * This file is a client component because it holds sidebar open/close state.
 */

import React, { useState } from "react";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { ChatInterface } from "@/components/ChatInterface";
import { Toaster } from "@/components/ui/sonner";

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    /*
     * Full-screen flex layout (5B.6.1 — no horizontal scroll on mobile).
     * `overflow-hidden` on the wrapper prevents body scroll; each region
     * manages its own overflow independently.
     */
    <div
      className="flex h-screen w-full flex-col overflow-hidden bg-background text-foreground font-sans"
      id="app-root"
    >
      {/* ── Fixed top bar (5B.4.1) ──────────────────────────────────────── */}
      <Header onMenuClick={() => setSidebarOpen(true)} />

      {/* ── Main content area ──────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden relative" role="main">
        {/* Left sidebar — collapses off-screen on mobile (5B.6.1) */}
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Chat / query area fills remaining space */}
        <section
          className="flex-1 overflow-hidden flex flex-col transition-all duration-300 w-full min-w-0"
          aria-label="Chat interface"
          id="chat-section"
        >
          <ChatInterface />
        </section>
      </div>

      {/*
       * Toast notifications (5B.5.6)
       * richColors enables green/red/amber distinction automatically.
       * position="bottom-right" keeps notifications out of the chat area.
       */}
      <Toaster richColors position="bottom-right" closeButton />
    </div>
  );
}
