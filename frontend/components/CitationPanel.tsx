"use client";

import React from "react";
import { Citation } from "@/store/store";
import { X, ExternalLink, Link as LinkIcon, ChevronDown, ChevronUp, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CitationPanelProps {
  citations: Citation[];
  isOpen: boolean;
  onClose: () => void;
}

// ── Relevance bar ──────────────────────────────────────────────────────────
function RelevanceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const colour =
    score >= 0.75
      ? "bg-emerald-500"
      : score >= 0.5
      ? "bg-amber-500"
      : "bg-destructive";
  const label =
    score >= 0.75 ? "High" : score >= 0.5 ? "Medium" : "Low";

  return (
    <div className="flex items-center gap-2.5">
      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${colour}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={`text-[11px] font-semibold uppercase tracking-wider min-w-[70px] text-right ${
          score >= 0.75
            ? "text-emerald-600 dark:text-emerald-400"
            : score >= 0.5
            ? "text-amber-600 dark:text-amber-400"
            : "text-destructive"
        }`}
      >
        {label} {pct}%
      </span>
    </div>
  );
}

// ── Single citation card ───────────────────────────────────────────────────
function CitationCard({
  citation,
  index,
}: {
  citation: Citation;
  index: number;
}) {
  const [expanded, setExpanded] = React.useState(false);
  const excerpt = citation.text_excerpt ?? "";
  const isLong = excerpt.length > 180;
  const displayed = expanded || !isLong ? excerpt : excerpt.slice(0, 180) + "…";

  return (
    <div className="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden hover:shadow-md transition-shadow duration-200">
      {/* Header */}
      <div className="px-3 py-2.5 border-b flex items-center gap-2 bg-muted/30">
        {/* Badge */}
        <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
          {index + 1}
        </div>
        <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="truncate flex-1 font-medium text-sm">
          {citation.source_document}
        </span>
        {citation.page_number != null && (
          <span className="text-[10px] text-muted-foreground shrink-0 ml-auto">
            p.{citation.page_number}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="px-3 py-3 space-y-2.5">
        {/* Relevance bar */}
        {citation.relevance_score != null && (
          <RelevanceBar score={citation.relevance_score} />
        )}

        {/* Excerpt */}
        <div>
          <p className="text-sm leading-relaxed text-muted-foreground italic">
            &ldquo;{displayed}&rdquo;
          </p>
          {isLong && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="mt-1 flex items-center gap-0.5 text-[10px] text-primary hover:underline"
            >
              {expanded ? (
                <>
                  Show less <ChevronUp className="h-3 w-3" />
                </>
              ) : (
                <>
                  Read more <ChevronDown className="h-3 w-3" />
                </>
              )}
            </button>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end pt-1 border-t border-border/40">
          <Button
            variant="link"
            className="h-auto p-0 text-[10px] flex items-center gap-1 text-muted-foreground hover:text-primary"
            onClick={() => {
              // In a real deployment this would open the source document viewer
              // For now we surface a helpful toast
              const detail = citation.page_number
                ? ` (page ${citation.page_number})`
                : "";
              window.alert(
                `Source: ${citation.source_document}${detail}\n\nFull excerpt:\n"${excerpt}"`
              );
            }}
          >
            View source <ExternalLink className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Panel ──────────────────────────────────────────────────────────────────
export function CitationPanel({ citations, isOpen, onClose }: CitationPanelProps) {
  if (!isOpen) return null;

  // Aggregate quality metrics
  const avgScore =
    citations.length > 0
      ? citations.reduce((s, c) => s + (c.relevance_score ?? 0), 0) /
        citations.length
      : 0;

  const highCount = citations.filter(
    (c) => (c.relevance_score ?? 0) >= 0.75
  ).length;

  return (
    <div className="w-80 shrink-0 border-l glass-panel flex flex-col h-full overflow-hidden absolute right-0 top-0 bottom-0 z-10 md:relative">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/30 shrink-0">
        <div className="flex items-center gap-2.5 font-semibold text-base">
          <LinkIcon className="h-4 w-4 text-primary" />
          <span>Sources</span>
          <span className="text-xs font-normal text-muted-foreground">
            ({citations.length})
          </span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={onClose}
          aria-label="Close citations"
        >
          <X className="h-3.5 w-3.5" />
          <span className="sr-only">Close citations</span>
        </Button>
      </div>

      {/* Quality summary bar */}
      {citations.length > 0 && (
        <div className="px-3 py-2 border-b bg-muted/10 shrink-0 flex items-center justify-between text-[11px] text-muted-foreground">
          <span>
            Avg. confidence:{" "}
            <span
              className={`font-semibold ${
                avgScore >= 0.75
                  ? "text-emerald-600 dark:text-emerald-400"
                  : avgScore >= 0.5
                  ? "text-amber-600 dark:text-amber-400"
                  : "text-destructive"
              }`}
            >
              {Math.round(avgScore * 100)}%
            </span>
          </span>
          <span>
            {highCount}/{citations.length} high quality
          </span>
        </div>
      )}

      {/* Citation list */}
      <div className="flex-1 overflow-auto p-3 space-y-3">
        {citations.length === 0 ? (
          <div className="text-sm text-muted-foreground text-center py-8">
            No citations available for this response.
          </div>
        ) : (
          citations.map((citation, idx) => (
            <CitationCard
              key={citation.citation_id ?? idx}
              citation={citation}
              index={idx}
            />
          ))
        )}
      </div>
    </div>
  );
}
