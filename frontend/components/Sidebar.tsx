"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useDocumentStore, useChatStore, useSettingsStore } from "@/store/store";
import {
  FileText,
  Settings as SettingsIcon,
  MessageSquare,
  Plus,
  Upload,
  Trash2,
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Search,
  Pin,
  Pencil,
  HardDrive,
  BarChart2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Settings } from "./Settings";
import { UserProfile } from "./UserProfile";
import { DocumentUpload } from "./DocumentUpload";
import { motion, AnimatePresence } from "framer-motion";
import { ApiService, ChatSessionPayload, DocumentPayload } from "@/lib/api";
import { toast } from "sonner";
import { useAuthStore } from "@/store/authStore";
import { useLogout } from "@/components/AuthProvider";
import { LogOut, ShieldCheck } from "lucide-react";
import Link from "next/link";

// ─────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

// ─────────────────────────────────────────────────────────
// Small helpers
// ─────────────────────────────────────────────────────────

function StatusIcon({ status }: { status: DocumentPayload["status"] }) {
  if (status === "processing")
    return <Loader2 className="h-3 w-3 shrink-0 text-amber-500 animate-spin" />;
  if (status === "error")
    return <AlertCircle className="h-3 w-3 shrink-0 text-destructive" />;
  return <CheckCircle2 className="h-3 w-3 shrink-0 text-emerald-500" />;
}

function fmtDate(ts: string) {
  try {
    return new Date(ts).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  } catch {
    return "";
  }
}

function fmtBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

/** Compute total bytes from the document store entries */
function totalStorageUsed(docs: ReturnType<typeof useDocumentStore.getState>["documents"]): number {
  return docs.reduce((sum, d) => sum + (d.file_size_bytes ?? 0), 0);
}

// ─────────────────────────────────────────────────────────
// Storage Stats Bar (Task 5B.8 — analytics section)
// ─────────────────────────────────────────────────────────

function StorageBar({
  documents,
}: {
  documents: ReturnType<typeof useDocumentStore.getState>["documents"];
}) {
  const usedBytes = totalStorageUsed(documents);
  const limitBytes = 1024 * 1024 * 1024; // 1 GB display cap
  const pct = Math.min((usedBytes / limitBytes) * 100, 100);
  const colour =
    pct > 80 ? "bg-destructive" : pct > 60 ? "bg-amber-500" : "bg-primary";

  if (documents.length === 0) return null;

  return (
    <div className="rounded-md border bg-muted/10 px-3 py-2 text-[11px] space-y-1.5">
      <div className="flex items-center justify-between text-muted-foreground">
        <span className="flex items-center gap-1">
          <HardDrive className="h-3 w-3" />
          Storage used
        </span>
        <span className="font-medium">{fmtBytes(usedBytes)}</span>
      </div>
      <div className="h-1 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${colour}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-muted-foreground/70">
        <span>
          {documents.filter((d) => d.status === "ready").length}/
          {documents.length} ready
        </span>
        <span>
          {documents.filter((d) => d.status === "processing").length > 0
            ? `${documents.filter((d) => d.status === "processing").length} indexing…`
            : ""}
        </span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { documents, setDocuments, removeDocument } = useDocumentStore();
  const { clearMessages } = useChatStore();
  const { user } = useAuthStore();

  const [uploadOpen, setUploadOpen] = useState(false);
  const { isSettingsOpen, setSettingsOpen } = useSettingsStore();
  const [history, setHistory] = useState<ChatSessionPayload[]>([]);
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<"docs" | "history">("docs");

  // IDs being mutated (for loading states)
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);
  const [mutatingHistId, setMutatingHistId] = useState<string | null>(null);

  // Rename state
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const renameInputRef = useRef<HTMLInputElement>(null);

  // ── data loaders ─────────────────────────────────────────

  const loadDocuments = useCallback(async () => {
    try {
      const res = await ApiService.listDocuments();
      setDocuments(
        res.documents.map((d) => ({
          doc_id: d.doc_id,
          filename: d.filename,
          file_size_bytes: d.file_size_bytes,
          status: d.status,
          upload_timestamp: d.upload_timestamp,
        }))
      );
    } catch {
      // silently fail — backend may not be running yet
    }
  }, [setDocuments]);

  const loadHistory = useCallback(async () => {
    try {
      const res = await ApiService.getSessions();
      setHistory(res.sessions);
    } catch {
      // silently fail
    }
  }, []);

  // Fetch data when component mounts or when user login state changes
  useEffect(() => {
    const init = async () => {
      if (user) {
        await loadDocuments();
        await loadHistory();
      } else {
        setDocuments([]);
        setHistory([]);
      }
    };
    void init();
  }, [user, loadDocuments, loadHistory, setDocuments]);

  // Reload history when switching to history tab
  useEffect(() => {
    if (user && activeTab === "history") {
      void loadHistory();
    }
  }, [user, activeTab, loadHistory]);

  // Poll while any document is still processing
  useEffect(() => {
    const anyProcessing = documents.some((d) => d.status === "processing");
    if (!anyProcessing) return;
    const timer = setInterval(loadDocuments, 5_000);
    return () => clearInterval(timer);
  }, [documents, loadDocuments]);

  // Listen for history refresh events dispatched by ChatInterface
  useEffect(() => {
    const handler = () => loadHistory();
    window.addEventListener("rag:history-updated", handler);
    return () => window.removeEventListener("rag:history-updated", handler);
  }, [loadHistory]);

  // Focus rename input when it appears
  useEffect(() => {
    if (renamingId) {
      setTimeout(() => renameInputRef.current?.focus(), 50);
    }
  }, [renamingId]);

  // ── handlers ─────────────────────────────────────────────

  const handleLoadChat = async (entry: ChatSessionPayload) => {
    if (window.innerWidth < 768 && onClose) onClose();
    try {
      const response = await ApiService.getSessionMessages(entry.session_id);
      clearMessages();
      useChatStore.getState().setActiveSessionId(entry.session_id);
      
      const mappedMessages = response.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        confidence: m.confidence !== null ? m.confidence : undefined,
        citations: m.citations as any,
        timestamp: new Date(m.created_at),
      }));

      useChatStore.getState().loadSessionMessages(mappedMessages);
    } catch (err) {
      console.error(err);
      toast.error("Failed to load session messages.");
    }
  };

  const handleNewChat = async () => {
    // Only clear the current conversation from the UI.
    // Do NOT call ApiService.clearHistory() — that wipes the entire DB history.
    clearMessages();
    onClose();
  };

  const handleDeleteDocument = async (docId: string) => {
    setDeletingDocId(docId);
    try {
      await ApiService.deleteDocument(docId);
      removeDocument(docId);
      toast.success("Document removed.");
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Failed to remove document."
      );
    } finally {
      setDeletingDocId(null);
    }
  };

  const handleDeleteHistory = async (sessionId: string) => {
    setMutatingHistId(sessionId);
    try {
      await ApiService.deleteSession(sessionId);
      setHistory((prev) => prev.filter((e) => e.session_id !== sessionId));
      toast.success("Chat removed.");
    } catch {
      toast.error("Failed to remove chat.");
    } finally {
      setMutatingHistId(null);
    }
  };

  // Pinning removed for sessions

  const startRename = (entry: ChatSessionPayload) => {
    setRenamingId(entry.session_id);
    setRenameValue(entry.title ?? "New Chat");
  };

  const commitRename = async (sessionId: string) => {
    const trimmed = renameValue.trim();
    setRenamingId(null);
    if (!trimmed) return;
    setMutatingHistId(sessionId);
    try {
      const updated = await ApiService.updateSession(sessionId, {
        title: trimmed,
      });
      setHistory((prev) =>
        prev.map((e) =>
          e.session_id === sessionId ? { ...e, title: updated.title } : e
        )
      );
    } catch {
      toast.error("Failed to rename chat.");
    } finally {
      setMutatingHistId(null);
    }
  };

  // ── filtered / sorted lists ───────────────────────────────

  const q = search.toLowerCase();

  const filteredDocs = documents.filter((d) =>
    d.filename.toLowerCase().includes(q)
  );

  const filteredHistory = history
    .filter((h) =>
      (h.title ?? "").toLowerCase().includes(q)
    )
    .sort((a, b) => {
      return new Date(b.last_message_at || b.created_at).getTime() - new Date(a.last_message_at || a.created_at).getTime();
    });

  // ── render ───────────────────────────────────────────────

  return (
    <>
      {/* Mobile backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm md:hidden"
            onClick={onClose}
          />
        )}
      </AnimatePresence>

      {/* Sidebar panel */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 md:static md:flex w-72 shrink-0 flex-col border-r glass-panel transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        {/* Mobile close bar */}
        <div className="flex h-14 items-center justify-between px-4 border-b md:hidden shrink-0">
          <span className="font-semibold text-sm">SecureHall-RAG</span>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {/* New Chat */}
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Button
              className="w-full justify-start gap-2.5 h-10 text-sm shadow-md shadow-primary/20 rounded-xl"
              onClick={handleNewChat}
              id="new-chat-btn"
            >
              <Plus className="h-4 w-4" />
              New Chat
            </Button>
          </motion.div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search docs & chats…"
              className="pl-9 h-9 text-sm bg-background/60 rounded-xl"
              id="sidebar-search"
              aria-label="Search documents and chat history"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-2 top-2 text-muted-foreground hover:text-foreground"
                aria-label="Clear search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Tab switcher (Task 5B.8 — improved navigation) */}
          <div className="flex rounded-xl border overflow-hidden text-sm">
            <button
              onClick={() => setActiveTab("docs")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 transition-colors ${
                activeTab === "docs"
                  ? "bg-primary text-primary-foreground font-medium"
                  : "bg-muted/30 text-muted-foreground hover:bg-muted/60"
              }`}
            >
              <FileText className="h-3.5 w-3.5" />
              Docs
              {documents.length > 0 && (
                <span className="rounded-full bg-current/20 px-1.5 text-[10px]">
                  {documents.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab("history")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 transition-colors ${
                activeTab === "history"
                  ? "bg-primary text-primary-foreground font-medium"
                  : "bg-muted/30 text-muted-foreground hover:bg-muted/60"
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              History
              {history.length > 0 && (
                <span className="rounded-full bg-current/20 px-1.5 text-[10px]">
                  {history.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab("docs")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 transition-colors ${
                activeTab === "docs" ? "" : "bg-muted/30 text-muted-foreground hover:bg-muted/60"
              }`}
              style={{ display: "none" }}
            />
          </div>

          {/* ── DOCUMENTS TAB ───────────────────────────────── */}
          <AnimatePresence mode="wait">
            {activeTab === "docs" && (
              <motion.section
                key="docs"
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 6 }}
                transition={{ duration: 0.12 }}
              >
                <div className="flex items-center justify-between mb-1.5 px-0.5">
                  <h3 className="text-[10px] font-semibold tracking-widest uppercase text-muted-foreground">
                    Knowledge Base
                  </h3>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5"
                    onClick={() => setUploadOpen(true)}
                    title="Upload document"
                    id="upload-doc-btn"
                  >
                    <Upload className="h-3.5 w-3.5" />
                  </Button>
                </div>

                {/* Storage analytics */}
                <StorageBar documents={documents} />

                <div className="space-y-0.5 mt-2">
                  {filteredDocs.length === 0 ? (
                    <div className="text-xs text-muted-foreground text-center border border-dashed rounded-md py-5">
                      {search ? (
                        <>No documents matching &quot;{search}&quot;</>
                      ) : (
                        <>
                          No documents yet —{" "}
                          <button
                            className="underline text-primary"
                            onClick={() => setUploadOpen(true)}
                          >
                            upload one
                          </button>
                        </>
                      )}
                    </div>
                  ) : (
                    <AnimatePresence>
                      {filteredDocs.map((doc) => (
                        <motion.div
                          key={doc.doc_id}
                          initial={{ opacity: 0, x: -6 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, scale: 0.95 }}
                          className="group flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-muted/50 transition-colors"
                        >
                          <FileText className="h-3.5 w-3.5 shrink-0 text-primary/70" />
                          <div className="flex-1 min-w-0">
                            <span className="block truncate text-xs">
                              {doc.filename}
                            </span>
                            <span className="text-[10px] text-muted-foreground/60">
                              {fmtBytes(doc.file_size_bytes)} ·{" "}
                              {fmtDate(doc.upload_timestamp)}
                            </span>
                          </div>
                          <StatusIcon status={doc.status} />
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5 opacity-0 group-hover:opacity-100 shrink-0"
                            onClick={() => handleDeleteDocument(doc.doc_id)}
                            disabled={deletingDocId === doc.doc_id}
                            title="Remove"
                          >
                            {deletingDocId === doc.doc_id ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Trash2 className="h-3 w-3 text-destructive" />
                            )}
                          </Button>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  )}
                </div>
              </motion.section>
            )}

            {/* ── HISTORY TAB ─────────────────────────────────── */}
            {activeTab === "history" && (
              <motion.section
                key="history"
                initial={{ opacity: 0, x: 6 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -6 }}
                transition={{ duration: 0.12 }}
              >
                <div className="flex items-center justify-between mb-1.5 px-0.5">
                  <h3 className="text-[10px] font-semibold tracking-widest uppercase text-muted-foreground">
                    Recent Chats
                  </h3>
                  {history.length > 0 && (
                    <button
                      onClick={handleNewChat}
                      className="text-[10px] text-muted-foreground hover:text-destructive transition-colors"
                      title="Clear all history"
                    >
                      Clear all
                    </button>
                  )}
                </div>

                {/* Analytics summary */}
                {history.length > 0 && !search && (
                  <div className="rounded-md border bg-muted/10 px-3 py-2 text-[11px] mb-2 flex items-center justify-between text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <BarChart2 className="h-3 w-3" />
                      {history.length} conversation{history.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                )}

                <div className="space-y-0.5">
                  {filteredHistory.length === 0 ? (
                    <div className="text-xs text-muted-foreground text-center border border-dashed rounded-md py-5">
                      {search ? (
                        <>No chats matching &quot;{search}&quot;</>
                      ) : (
                        "No chat history yet"
                      )}
                    </div>
                  ) : (
                    filteredHistory.map((entry) => (
                      <div
                        key={entry.session_id}
                        onClick={() => handleLoadChat(entry)}
                        className="group rounded-md px-2 py-2 transition-colors hover:bg-muted/50 cursor-pointer"
                      >
                        <div className="flex items-start gap-2">
                          {/* Icon */}
                          <div className="mt-0.5 shrink-0">
                            <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
                          </div>

                          {/* Title / rename input */}
                          <div className="flex-1 min-w-0">
                            {renamingId === entry.session_id ? (
                              <Input
                                ref={renameInputRef}
                                value={renameValue}
                                onChange={(e) => setRenameValue(e.target.value)}
                                onBlur={() => commitRename(entry.session_id)}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter")
                                    commitRename(entry.session_id);
                                  if (e.key === "Escape")
                                    setRenamingId(null);
                                }}
                                className="h-5 text-xs px-1 py-0"
                              />
                            ) : (
                              <p
                                className="truncate text-xs font-medium text-muted-foreground group-hover:text-foreground"
                                title={entry.title || "New Chat"}
                              >
                                {entry.title || "New Chat"}
                              </p>
                            )}
                            <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                              {fmtDate(entry.last_message_at || entry.created_at)}
                              {entry.message_count > 0 &&
                                ` · ${entry.message_count} msg${
                                  entry.message_count !== 1 ? "s" : ""
                                }`}
                            </p>
                          </div>

                          {/* Context actions — visible on hover */}
                          <div className="flex items-center gap-0 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-5 w-5 hover:text-primary"
                              title="Rename"
                              onClick={(e) => {
                                e.stopPropagation();
                                startRename(entry);
                              }}
                            >
                              <Pencil className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-5 w-5 text-destructive/70 hover:text-destructive hover:bg-destructive/10"
                              title="Delete"
                              disabled={mutatingHistId === entry.session_id}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteHistory(entry.session_id);
                              }}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </motion.section>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="shrink-0 p-3 border-t space-y-1">
          {/* Admin Dashboard Button */}
          {user && (user.role === 'admin' || user.role === 'hr') && (
            <Link href="/admin" className="w-full block">
              <Button
                variant="ghost"
                className="w-full justify-start gap-2 h-9 text-sm"
                id="admin-dashboard-btn"
              >
                <ShieldCheck className="h-4 w-4" />
                Admin Dashboard
              </Button>
            </Link>
          )}

          <Button
            variant="ghost"
            className="w-full justify-start gap-2 h-9 text-sm"
            onClick={() => setSettingsOpen(true)}
            id="settings-btn"
          >
            <SettingsIcon className="h-4 w-4" />
            Settings
          </Button>

          {/* User profile + logout */}
          <UserFooter />
        </div>
      </aside>

      {/* Dialogs */}
      <DocumentUpload
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onUploaded={() => {
          // Refresh doc list after upload
          setTimeout(loadDocuments, 500);
        }}
      />
      <Settings open={isSettingsOpen} onOpenChange={setSettingsOpen} />
      <UserProfile />
    </>
  );
}

// ── User footer component ───────────────────────────────────────────────────
function UserFooter() {
  const { user } = useAuthStore();
  const logout = useLogout();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || !user) return null;

  const initials = (user.full_name ?? user.username)
    .split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);

  const roleColors = {
    admin: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
    hr:    'bg-blue-500/20 text-blue-300 border-blue-500/30',
    employee: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
  };

  return (
    <div className="mt-2 px-3 pb-2">
      <div className="flex items-center gap-3 p-3 rounded-xl bg-background/50 glass-panel border border-border/50 shadow-sm transition-all hover:shadow-md">
        {/* Avatar */}
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary to-blue-500 flex items-center justify-center text-white text-sm font-bold shrink-0 shadow-sm shadow-primary/30">
          {initials}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate">
            {user.full_name ?? user.username}
          </p>
          <span className={`inline-flex items-center text-[10px] px-1.5 py-0.5 rounded border bg-background/80 text-muted-foreground border-border/60 mt-0.5 font-medium shadow-sm`}>
            {user.role}
          </span>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-1">
          <button
            onClick={logout}
            title="Sign out"
            className="w-7 h-7 flex items-center justify-center rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
