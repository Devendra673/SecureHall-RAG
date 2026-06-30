"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { useChatStore, Citation } from "@/store/store";
import { ResponseDisplay } from "./ResponseDisplay";
import { CitationPanel } from "./CitationPanel";
import {
  Send,
  User as UserIcon,
  Bot,
  Download,
  ChevronDown,
  Moon,
  Sun,
  Monitor,
  FileText,
  FileJson,
  File,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { motion, AnimatePresence } from "framer-motion";
import { ApiService } from "@/lib/api";
import { toast } from "sonner";
import { useTheme } from "next-themes";

/**
 * Each assistant message stores the backend answer_id separately so
 * ResponseDisplay can use it for the real feedback API call.
 */
interface AssistantMeta {
  /** backend answer_id — the only correct id for API calls */
  answerId: string;
}

const metaMap = new Map<string, AssistantMeta>();

// ── Export helpers ──────────────────────────────────────────────────────────

function buildMarkdown(messages: ReturnType<typeof useChatStore.getState>["messages"]): string {
  let md = `# SecureHall-RAG — Exported Conversation\n_${new Date().toLocaleString()}_\n\n---\n\n`;
  messages.forEach((m) => {
    md += `**${m.role === "user" ? "You" : "Assistant"}**\n\n${m.content}\n\n---\n\n`;
  });
  return md;
}

function downloadBlob(content: string, mime: string, filename: string) {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ─────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────

export function ChatInterface() {
  const { activeSessionId, setActiveSessionId, messages, isThinking, addMessage, updateMessage, setThinking } =
    useChatStore();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const cycleTheme = () => {
    const next = theme === "dark" ? "light" : theme === "light" ? "system" : "dark";
    setTheme(next);
  };

  const [input, setInput] = useState("");
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ── Auto-scroll ──────────────────────────────────────────
  const scrollToBottom = useCallback((smooth = true) => {
    messagesEndRef.current?.scrollIntoView({
      behavior: smooth ? "smooth" : "instant",
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking, scrollToBottom]);

  // Track whether user has scrolled up
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const handleScroll = () => {
      const distFromBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight;
      setShowScrollButton(distFromBottom > 200);
    };
    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // ── Auto-resize textarea ─────────────────────────────────
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    }
  }, [input]);

  // ── Keyboard shortcuts ────────────────────────────────────
  useEffect(() => {
    const handleGlobalKey = (e: KeyboardEvent) => {
      // Ctrl/Cmd + K: focus input
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        textareaRef.current?.focus();
      }
      // Escape: close citation panel
      if (e.key === "Escape" && panelOpen) {
        setPanelOpen(false);
      }
    };
    window.addEventListener("keydown", handleGlobalKey);
    return () => window.removeEventListener("keydown", handleGlobalKey);
  }, [panelOpen]);

  // ── Export ──────────────────────────────────────────────
  const exportMarkdown = useCallback(() => {
    if (messages.length === 0) {
      toast.error("Nothing to export yet.");
      return;
    }
    const content = buildMarkdown(messages);
    downloadBlob(content, "text/markdown", `chat-export-${Date.now()}.md`);
    toast.success("Conversation exported as Markdown");
    setExportMenuOpen(false);
  }, [messages]);

  const exportText = useCallback(() => {
    if (messages.length === 0) {
      toast.error("Nothing to export yet.");
      return;
    }
    let text = `SecureHall-RAG — Conversation Export\n${new Date().toLocaleString()}\n${"=".repeat(50)}\n\n`;
    messages.forEach((m) => {
      text += `[${m.role === "user" ? "YOU" : "ASSISTANT"}]\n${m.content}\n\n${"-".repeat(40)}\n\n`;
    });
    downloadBlob(text, "text/plain", `chat-export-${Date.now()}.txt`);
    toast.success("Conversation exported as plain text");
    setExportMenuOpen(false);
  }, [messages]);

  const exportJson = useCallback(() => {
    if (messages.length === 0) {
      toast.error("Nothing to export yet.");
      return;
    }
    const data = {
      exported_at: new Date().toISOString(),
      message_count: messages.length,
      messages: messages.map((m) => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
        citation_count: m.citations?.length ?? 0,
        confidence: m.confidence ?? null,
      })),
    };
    downloadBlob(
      JSON.stringify(data, null, 2),
      "application/json",
      `chat-export-${Date.now()}.json`
    );
    toast.success("Conversation exported as JSON");
    setExportMenuOpen(false);
  }, [messages]);

  // ── Send ────────────────────────────────────────────────
  const handleSend = async () => {
    const query = input.trim();
    if (!query || isThinking) return;

    // Add user bubble immediately
    const userMsgId = `user-${Date.now()}`;
    addMessage({
      id: userMsgId,
      role: "user",
      content: query,
      timestamp: new Date(),
    });
    setInput("");
    setThinking(true);

    // Reserve a local ID for the assistant bubble
    const localMsgId = `assistant-${Date.now()}`;
    addMessage({
      id: localMsgId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
    });

    // Prepare history payload from existing messages (before we add the new user query to the local store)
    const historyPayload = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      let accumulatedText = "";
      
      await ApiService.submitQueryStream(
        { query, session_id: activeSessionId || undefined, history: historyPayload },
        // onMetadata
        (metadata) => {
          updateMessage(localMsgId, {
            confidence: metadata.confidence,
            citations: metadata.citations as unknown as Citation[],
            uncertainty_tier: metadata.uncertainty_tier,
          });
        },
        // onChunk
        (textChunk) => {
          accumulatedText += textChunk;
          updateMessage(localMsgId, { content: accumulatedText + "▌" });
        },
        // onDone
        (answerId?: string, sessionId?: string) => {
          if (answerId) {
            metaMap.set(localMsgId, { answerId });
          }
          if (sessionId && !activeSessionId) {
            setActiveSessionId(sessionId);
          }
          updateMessage(localMsgId, { content: accumulatedText });
          window.dispatchEvent(new CustomEvent("rag:history-updated"));
          setThinking(false);
        },
        // onError
        (err) => {
          const msg = err.message || "Query failed. Is the backend running?";
          toast.error(msg);
          updateMessage(localMsgId, { content: `⚠️ ${msg}` });
          setThinking(false);
        }
      );

      // The backend answer_id isn't returned immediately in the stream right now, 
      // but if we updated the SSE endpoint to return it in the done event, we could set it.
      // For now, feedback might not work perfectly until we refresh or inject the answer_id.
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Query failed.";
      toast.error(msg);
      updateMessage(localMsgId, { content: `⚠️ ${msg}` });
      setThinking(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const openCitations = (citations?: Citation[]) => {
    if (citations && citations.length > 0) {
      setActiveCitations(citations);
      setPanelOpen(true);
    }
  };

  return (
    <div className="flex w-full h-full overflow-hidden bg-background">
      {/* Main area */}
      <div className="flex-1 flex flex-col h-full min-w-0">
        {/* Top bar */}
        <div className="flex items-center justify-between px-5 py-2.5 border-b glass-panel bg-muted/10 shrink-0">
          <span className="text-sm font-medium text-muted-foreground">
            Current Session
            {messages.length > 0 && (
              <span className="ml-2 text-xs text-muted-foreground/60">
                ({messages.length} message{messages.length !== 1 ? "s" : ""})
              </span>
            )}
          </span>

          <div className="flex items-center gap-2">
            {/* Theme Toggle in Chat */}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-foreground"
              onClick={cycleTheme}
              aria-label="Toggle theme"
            >
              {!mounted ? (
                <Monitor className="h-4 w-4" />
              ) : theme === "dark" ? (
                <Moon className="h-4 w-4" />
              ) : theme === "light" ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Monitor className="h-4 w-4" />
              )}
            </Button>

            {/* Export dropdown */}
            <div className="relative">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs gap-1.5 font-medium border-white/20 dark:border-white/10"
              onClick={() => setExportMenuOpen((v) => !v)}
              disabled={messages.length === 0}
            >
              <Download className="h-3.5 w-3.5 text-primary" />
              Export
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </Button>

            <AnimatePresence>
              {exportMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -4, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -4, scale: 0.97 }}
                  transition={{ duration: 0.12 }}
                  className="absolute right-0 top-full mt-1.5 z-50 w-48 rounded-xl border border-border/80 bg-popover/95 text-popover-foreground backdrop-blur-md shadow-xl overflow-hidden p-1 flex flex-col gap-0.5"
                >
                  {[
                    { label: "Markdown (.md)", icon: <FileText className="h-3.5 w-3.5 text-blue-500/80" />, action: exportMarkdown },
                    { label: "Plain Text (.txt)", icon: <File className="h-3.5 w-3.5 text-muted-foreground/80" />, action: exportText },
                    { label: "JSON (.json)", icon: <FileJson className="h-3.5 w-3.5 text-purple-500/80" />, action: exportJson },
                  ].map(({ label, icon, action }) => (
                    <button
                      key={label}
                      onClick={action}
                      className="w-full flex items-center gap-2 text-left px-2.5 py-1.5 text-xs text-popover-foreground hover:bg-accent hover:text-accent-foreground rounded-lg transition-all duration-150 cursor-pointer font-medium"
                    >
                      {icon}
                      <span>{label}</span>
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Click-away to close */}
            {exportMenuOpen && (
              <div
                className="fixed inset-0 z-40"
                onClick={() => setExportMenuOpen(false)}
              />
            )}
            </div>
          </div>
        </div>

        {/* Messages */}
        <div
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto px-4 py-6 space-y-6 relative"
        >
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto px-4">
              <div className="h-20 w-20 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mb-6 text-primary shadow-lg shadow-primary/10">
                <Bot className="h-10 w-10" />
              </div>
              <h2 className="text-2xl md:text-3xl font-bold mb-3 tracking-tight">
                How can I help you today?
              </h2>
              <p className="text-muted-foreground text-base leading-relaxed mb-6">
                Upload documents in the sidebar, then ask anything about them.
                Every answer includes citations so you can verify the facts.
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {[
                  "What are the key findings?",
                  "Summarize the document",
                  "Compare the policies",
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); textareaRef.current?.focus(); }}
                    className="text-sm px-4 py-2 rounded-xl border border-border/60 bg-card/50 text-muted-foreground hover:text-foreground hover:border-primary/40 hover:bg-primary/5 transition-all duration-200"
                  >
                    {q}
                  </button>
                ))}
              </div>
              <p className="text-xs text-muted-foreground/50 mt-6">
                Press{" "}
                <kbd className="px-1.5 py-0.5 rounded border bg-muted text-[10px] font-mono">
                  Ctrl K
                </kbd>{" "}
                to focus the input anytime.
              </p>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.18 }}
                    className={`flex gap-3 ${
                      msg.role === "user" ? "flex-row-reverse" : "flex-row"
                    }`}
                  >
                    {/* Avatar */}
                    <div
                      className={`shrink-0 h-8 w-8 rounded-full flex items-center justify-center mt-0.5 ${
                        msg.role === "user"
                          ? "bg-secondary text-secondary-foreground"
                          : "bg-primary text-primary-foreground"
                      }`}
                    >
                      {msg.role === "user" ? (
                        <UserIcon className="h-4 w-4" />
                      ) : (
                        <Bot className="h-4 w-4" />
                      )}
                    </div>

                    {/* Bubble */}
                    <div
                      className={`flex flex-col max-w-[80%] ${
                        msg.role === "user" ? "items-end" : "items-start"
                      }`}
                    >
                      {msg.role === "user" ? (
                    <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-5 py-3 text-[15px] leading-relaxed whitespace-pre-wrap shadow-md shadow-primary/20">
                          {msg.content}
                        </div>
                      ) : (
                        <div className="glass-panel bg-card/60 rounded-2xl rounded-tl-sm px-5 py-4 border text-[15px] leading-relaxed shadow-sm w-full">
                          <ResponseDisplay
                            content={msg.content}
                            citations={msg.citations}
                            answerId={metaMap.get(msg.id)?.answerId ?? msg.id}
                            confidence={msg.confidence}
                            uncertaintyTier={msg.uncertainty_tier}
                            onShowCitations={() => openCitations(msg.citations)}
                          />
                        </div>
                      )}

                      {/* Timestamp */}
                      <p className="text-[10px] text-muted-foreground/50 mt-1 px-1">
                        {msg.timestamp instanceof Date
                          ? msg.timestamp.toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : ""}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Thinking dots */}
              {isThinking && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3"
                >
                  <div className="shrink-0 h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center shadow-md shadow-primary/20">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="glass-panel bg-card/60 rounded-2xl rounded-tl-sm px-4 py-3 border shadow-sm flex items-center gap-1.5 h-11">
                    {["-0.3s", "-0.15s", "0s"].map((d, i) => (
                      <span
                        key={i}
                        className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce"
                        style={{ animationDelay: d }}
                      />
                    ))}
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Scroll-to-bottom button */}
          <AnimatePresence>
            {showScrollButton && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1.5 rounded-full bg-primary text-primary-foreground px-4 py-1.5 text-xs font-medium shadow-lg hover:bg-primary/90 transition-colors"
                onClick={() => scrollToBottom()}
              >
                <ChevronDown className="h-3.5 w-3.5" />
                Scroll to latest
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        {/* Input */}
        <div className="shrink-0 p-4 border-t glass-panel bg-background/50">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end gap-2 bg-background/60 glass-panel rounded-xl border px-3 py-2 focus-within:ring-2 focus-within:ring-primary/40 focus-within:border-primary/50 focus-within:shadow-[0_4px_20px_rgba(0,0,0,0.05)] focus-within:-translate-y-0.5 transition-all duration-300">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your documents… (Enter to send, Shift+Enter for newline)"
                className="min-h-[48px] max-h-[200px] flex-1 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0 px-1 py-2.5 text-[15px] leading-relaxed"
                rows={1}
                disabled={isThinking}
                aria-label="Query input"
                id="chat-input"
              />
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="mb-0.5">
                <Button
                  size="icon"
                  className="shrink-0 h-9 w-9 rounded-lg shadow-md shadow-primary/20"
                  onClick={handleSend}
                  disabled={!input.trim() || isThinking}
                  aria-label="Send query"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </motion.div>
            </div>
            <p className="text-center mt-2 text-[11px] text-muted-foreground">
              Verify important information using the provided citations.
            </p>
          </div>
        </div>
      </div>

      {/* Citation panel */}
      <CitationPanel
        citations={activeCitations}
        isOpen={panelOpen}
        onClose={() => setPanelOpen(false)}
      />
    </div>
  );
}
