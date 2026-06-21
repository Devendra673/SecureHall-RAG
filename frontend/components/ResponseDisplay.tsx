"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import {
  Copy,
  ThumbsUp,
  ThumbsDown,
  Check,
  BookOpen,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiService } from "@/lib/api";
import { Citation } from "@/store/store";
import { toast } from "sonner";

// ─────────────────────────────────────────────────────────
// Confidence badge
// ─────────────────────────────────────────────────────────
function ConfidenceBadge({ score }: { score: number }) {
  if (score >= 0.75) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 bg-emerald-100/60 dark:bg-emerald-900/30 border border-emerald-300/50 dark:border-emerald-700/50 rounded-full px-3 py-1">
        <ShieldCheck className="h-3.5 w-3.5" />
        High Confidence · {Math.round(score * 100)}%
      </span>
    );
  }
  if (score >= 0.5) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400 bg-amber-100/60 dark:bg-amber-900/30 border border-amber-300/50 dark:border-amber-700/50 rounded-full px-3 py-1">
        <AlertTriangle className="h-3.5 w-3.5" />
        Medium Confidence · {Math.round(score * 100)}%
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-red-700 dark:text-red-400 bg-red-100/60 dark:bg-red-900/30 border border-red-300/50 dark:border-red-700/50 rounded-full px-3 py-1">
      <ShieldAlert className="h-3.5 w-3.5" />
      Low Confidence · {Math.round(score * 100)}%
    </span>
  );
}

// ─────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────
interface ResponseDisplayProps {
  content: string;
  citations?: Citation[];
  /** The backend answer_id — required for feedback & citation panel */
  answerId: string;
  /** Overall response confidence score (0–1) */
  confidence?: number;
  onShowCitations?: () => void;
}

// ─────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────
export function ResponseDisplay({
  content,
  citations,
  answerId,
  confidence,
  onShowCitations,
}: ResponseDisplayProps) {
  const [copied, setCopied] = React.useState(false);
  const [feedback, setFeedback] = React.useState<"up" | "down" | null>(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.success("Copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy");
    }
  };

  const handleFeedback = async (isPositive: boolean) => {
    if (feedback !== null) return; // already voted
    const next = isPositive ? "up" : "down";
    setFeedback(next);
    try {
      await ApiService.submitFeedback(answerId, { is_positive: isPositive });
      toast.success("Thanks for your feedback!");
    } catch {
      toast.error("Could not submit feedback.");
      setFeedback(null);
    }
  };

  // Don't show badge during typewriter, and hide it for simple conversational messages (no citations)
  const isStreaming = content.endsWith("▌");
  const showBadge = !isStreaming && confidence != null && content.length > 0 && citations && citations.length > 0;

  return (
    <div className="flex flex-col gap-3 w-full">
      {/* Confidence badge */}
      {showBadge && (
        <div>
          <ConfidenceBadge score={confidence!} />
        </div>
      )}

      {/* Markdown content */}
      <div className="prose prose-base dark:prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-muted/50 prose-pre:border">
        <ReactMarkdown>{content.replace(/▌$/, "")}</ReactMarkdown>
      </div>

      {/* Action bar — only shown when streaming is done */}
      {!isStreaming && content.length > 0 && (
        <div className="flex items-center justify-between pt-2 border-t border-border/40">
          {/* Citations button */}
          <div>
            {citations && citations.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs gap-1.5 text-muted-foreground hover:text-primary hover:border-primary/40 transition-colors"
                onClick={onShowCitations}
                aria-label={`View ${citations.length} sources`}
              >
                <BookOpen className="h-3.5 w-3.5" />
                {citations.length} source{citations.length !== 1 ? "s" : ""}
              </Button>
            )}
          </div>

          {/* Utility buttons */}
          <div className="flex items-center gap-0.5">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 hover:bg-muted/50"
              onClick={handleCopy}
              aria-label="Copy response"
            >
              {copied ? (
                <Check className="h-4 w-4 text-emerald-500" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={`h-8 w-8 ${
                feedback === "up"
                  ? "text-primary bg-primary/10"
                  : "hover:bg-muted/50"
              }`}
              onClick={() => handleFeedback(true)}
              disabled={feedback !== null}
              aria-label="Thumbs up"
            >
              <ThumbsUp className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={`h-8 w-8 ${
                feedback === "down"
                  ? "text-destructive bg-destructive/10"
                  : "hover:bg-muted/50"
              }`}
              onClick={() => handleFeedback(false)}
              disabled={feedback !== null}
              aria-label="Thumbs down"
            >
              <ThumbsDown className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
