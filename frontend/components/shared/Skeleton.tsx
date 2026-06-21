/**
 * Shared skeleton loaders — Phase 5B.5.3 (Loading States)
 *
 * Provides:
 *  • SkeletonLine   — single text-line placeholder
 *  • SkeletonBlock  — paragraph / card placeholder
 *  • MessageSkeleton — animated assistant-bubble placeholder
 */
"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

/** Single shimmering line */
export function SkeletonLine({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "h-3.5 rounded-full bg-muted/60 animate-pulse",
        className
      )}
      aria-hidden="true"
    />
  );
}

/** Paragraph block — 3 lines of varying width */
export function SkeletonBlock({ className }: SkeletonProps) {
  return (
    <div className={cn("space-y-2", className)} aria-hidden="true">
      <SkeletonLine className="w-full" />
      <SkeletonLine className="w-4/5" />
      <SkeletonLine className="w-3/5" />
    </div>
  );
}

/**
 * Full assistant-message skeleton — used while the RAG pipeline is
 * generating a response (5B.5.3).
 */
export function MessageSkeleton() {
  return (
    <div className="flex gap-3 animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
      {/* Avatar */}
      <div className="shrink-0 h-8 w-8 rounded-full bg-muted animate-pulse" aria-hidden="true" />

      {/* Content bubble */}
      <div className="flex flex-col gap-2 max-w-[70%] w-full bg-muted/30 rounded-2xl rounded-tl-sm px-4 py-4 border shadow-sm">
        <SkeletonLine className="w-full" />
        <SkeletonLine className="w-11/12" />
        <SkeletonLine className="w-3/4" />
        <SkeletonLine className="w-1/2 mt-1" />
      </div>
    </div>
  );
}

/** Small card skeleton for document list items */
export function DocumentSkeleton() {
  return (
    <div className="flex items-center gap-2 px-2 py-1.5 rounded-md" aria-hidden="true">
      <div className="h-3.5 w-3.5 rounded bg-muted animate-pulse shrink-0" />
      <div className="flex-1 h-3 rounded-full bg-muted animate-pulse" />
      <div className="h-3 w-3 rounded-full bg-muted animate-pulse shrink-0" />
    </div>
  );
}
