"use client";

import React, { useState, useRef } from "react";
import { useDocumentStore } from "@/store/store";
import { useAuthStore } from "@/store/authStore";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  File,
  FileType,
  X,
} from "lucide-react";
import { ApiService } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

// ─────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────
interface DocumentUploadProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called after at least one file uploads successfully */
  onUploaded?: () => void;
}

interface UploadEntry {
  file: File;
  status: "pending" | "uploading" | "done" | "error";
  progress: number;
  errorMsg?: string;
}

// ─────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────
const ALLOWED_TYPES = [".pdf", ".docx", ".txt", ".md"] as const;
const MAX_SIZE_MB = 50;

function fmtBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

function FileIcon({ name }: { name: string }) {
  const ext = name.split(".").pop()?.toLowerCase();
  if (ext === "pdf")
    return <FileType className="h-4 w-4 shrink-0 text-red-500/80" />;
  if (ext === "docx" || ext === "doc")
    return <FileType className="h-4 w-4 shrink-0 text-blue-500/80" />;
  if (ext === "txt" || ext === "md")
    return <File className="h-4 w-4 shrink-0 text-muted-foreground" />;
  return <FileText className="h-4 w-4 shrink-0 text-primary/70" />;
}

function validateFile(file: File): string | null {
  const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
  if (!(ALLOWED_TYPES as readonly string[]).includes(ext)) {
    return `"${file.name}": unsupported type. Allowed: PDF, DOCX, TXT, MD.`;
  }
  if (file.size > MAX_SIZE_MB * 1_048_576) {
    return `"${file.name}": file is ${fmtBytes(file.size)} — limit is ${MAX_SIZE_MB} MB.`;
  }
  return null;
}

// ─────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────
export function DocumentUpload({
  open,
  onOpenChange,
  onUploaded,
}: DocumentUploadProps) {
  const { addDocument } = useDocumentStore();
  const { user } = useAuthStore();
  const [isDragging, setIsDragging] = useState(false);
  const [accessLevel, setAccessLevel] = useState<"all" | "hr" | "admin">("all");
  const [entries, setEntries] = useState<UploadEntry[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── helpers ──────────────────────────────────────────────
  const resetState = () => {
    setEntries([]);
    setIsRunning(false);
    setIsDragging(false);
    setAccessLevel("all");
  };

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen && !isRunning) resetState();
    if (!isRunning) onOpenChange(nextOpen);
  };

  const updateEntry = (index: number, patch: Partial<UploadEntry>) => {
    setEntries((prev) =>
      prev.map((e, i) => (i === index ? { ...e, ...patch } : e))
    );
  };

  const removeEntry = (index: number) => {
    setEntries((prev) => prev.filter((_, i) => i !== index));
  };

  // ── file selection ────────────────────────────────────────
  const queueFiles = (files: FileList | File[] | null) => {
    if (!files || files.length === 0) return;

    const newEntries: UploadEntry[] = [];
    for (const file of Array.from(files)) {
      const err = validateFile(file);
      if (err) {
        toast.error(err);
        continue;
      }
      // Skip duplicates already in queue
      if (entries.some((e) => e.file.name === file.name && e.file.size === file.size)) {
        toast.info(`"${file.name}" is already queued.`);
        continue;
      }
      newEntries.push({ file, status: "pending", progress: 0 });
    }

    if (newEntries.length > 0) {
      setEntries((prev) => [...prev, ...newEntries]);
    }
  };

  // ── drag & drop ───────────────────────────────────────────
  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };
  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    queueFiles(e.dataTransfer.files);
  };

  // ── upload ────────────────────────────────────────────────
  const startUpload = async () => {
    const pending = entries.filter((e) => e.status === "pending");
    if (pending.length === 0) return;
    setIsRunning(true);

    let uploadedCount = 0;

    for (let i = 0; i < entries.length; i++) {
      const entry = entries[i];
      if (entry.status !== "pending") continue;

      updateEntry(i, { status: "uploading", progress: 0 });

      try {
        const result = await ApiService.uploadFile(entry.file, accessLevel, (pct) => {
          updateEntry(i, { progress: pct });
        });

        updateEntry(i, { status: "done", progress: 100 });
        uploadedCount++;

        // Optimistically add to global store
        addDocument({
          doc_id: result.doc_id,
          filename: result.filename,
          file_size_bytes: result.file_size_bytes,
          status: "processing",
          upload_timestamp: new Date().toISOString(),
        });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        updateEntry(i, { status: "error", errorMsg: msg });
        toast.error(msg);
      }
    }

    setIsRunning(false);

    if (uploadedCount > 0) {
      toast.success(
        `${uploadedCount} file${uploadedCount > 1 ? "s" : ""} uploaded — indexing in progress.`
      );
      onUploaded?.();
      setTimeout(() => {
        resetState();
        onOpenChange(false);
      }, 800);
    }
  };

  const pendingCount = entries.filter((e) => e.status === "pending").length;
  const errorCount = entries.filter((e) => e.status === "error").length;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[540px] glass-panel border shadow-2xl">
        <DialogHeader>
          <DialogTitle>Upload Documents</DialogTitle>
          <DialogDescription>
            Add PDF, DOCX, TXT, or MD files to your knowledge base (max {MAX_SIZE_MB} MB each).
          </DialogDescription>
        </DialogHeader>

        {/* Drop zone */}
        <div
          className={`mt-2 flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 cursor-pointer transition-all duration-200 ${
            isDragging
              ? "border-primary bg-primary/8 scale-[1.01]"
              : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30"
          }`}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => !isRunning && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md"
            className="hidden"
            onChange={(e) => queueFiles(e.target.files)}
          />
          <div className="rounded-full bg-primary/10 p-4 mb-3 text-primary">
            <UploadCloud className="h-8 w-8" />
          </div>
          <p className="text-sm font-semibold">
            {isDragging ? "Drop files here" : "Click to browse or drag and drop"}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            PDF · DOCX · TXT · MD — up to {MAX_SIZE_MB} MB each
          </p>
        </div>

        {/* File list */}
        {entries.length > 0 && (
          <div className="mt-3 space-y-1.5 max-h-52 overflow-y-auto pr-1">
            {entries.map((entry, i) => (
              <div
                key={i}
                className={`flex items-center gap-2.5 rounded-lg border px-3 py-2 text-sm transition-colors ${
                  entry.status === "done"
                    ? "border-emerald-500/30 bg-emerald-50/30 dark:bg-emerald-900/10"
                    : entry.status === "error"
                    ? "border-destructive/30 bg-destructive/5"
                    : "bg-muted/20"
                }`}
              >
                <FileIcon name={entry.file.name} />
                <div className="flex-1 min-w-0">
                  <p className="truncate font-medium text-xs">{entry.file.name}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {fmtBytes(entry.file.size)}
                  </p>
                  {entry.status === "uploading" && (
                    <div className="mt-1 h-1 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-200"
                        style={{ width: `${entry.progress}%` }}
                      />
                    </div>
                  )}
                  {entry.status === "error" && (
                    <p className="text-[10px] text-destructive leading-tight mt-0.5">
                      {entry.errorMsg}
                    </p>
                  )}
                </div>

                {/* Status icons */}
                {entry.status === "done" && (
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                )}
                {entry.status === "error" && (
                  <AlertCircle className="h-4 w-4 text-destructive shrink-0" />
                )}
                {entry.status === "uploading" && (
                  <span className="text-[10px] text-muted-foreground shrink-0">
                    {entry.progress}%
                  </span>
                )}
                {entry.status === "pending" && !isRunning && (
                  <button
                    onClick={() => removeEntry(i)}
                    className="h-5 w-5 shrink-0 flex items-center justify-center rounded hover:bg-muted transition-colors"
                    aria-label="Remove file"
                  >
                    <X className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Error count warning */}
        {errorCount > 0 && !isRunning && (
          <p className="text-xs text-destructive text-center">
            {errorCount} file{errorCount > 1 ? "s" : ""} failed. You can retry
            or remove them.
          </p>
        )}

        {/* Access Level Selector */}
        {user && (user.role === "admin" || user.role === "hr") && pendingCount > 0 && !isRunning && (
          <div className="mt-2 px-1 flex items-center justify-between">
            <label htmlFor="accessLevel" className="text-sm font-medium text-muted-foreground">
              Who can access these files?
            </label>
            <select
              id="accessLevel"
              value={accessLevel}
              onChange={(e) => setAccessLevel(e.target.value as "all" | "hr" | "admin")}
              className="text-sm bg-muted text-foreground rounded border border-input px-2 py-1 outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="all">Everyone (All)</option>
              <option value="hr">HR & Admin</option>
              {user.role === "admin" && <option value="admin">Admin Only</option>}
            </select>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 mt-2">
          <Button
            variant="outline"
            className="flex-1"
            disabled={isRunning}
            onClick={() => {
              resetState();
              onOpenChange(false);
            }}
          >
            Cancel
          </Button>
          <Button
            className="flex-1"
            disabled={pendingCount === 0 || isRunning}
            onClick={startUpload}
          >
            {isRunning
              ? "Uploading…"
              : pendingCount > 0
              ? `Upload ${pendingCount} file${pendingCount > 1 ? "s" : ""}`
              : "Upload"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
