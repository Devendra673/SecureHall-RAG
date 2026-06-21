"use client";

import React, { useEffect, useRef } from "react";
import { useSettingsStore } from "@/store/store";
import { useTheme } from "next-themes";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ApiService } from "@/lib/api";
import { toast } from "sonner";
import { Save, RotateCcw } from "lucide-react";

interface SettingsProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function Settings({ open, onOpenChange }: SettingsProps) {
  const { settings, updateSettings } = useSettingsStore();
  const { theme, setTheme } = useTheme();
  const isSaving = useRef(false);

  // ── Load persisted settings from backend on first open ──────────────────
  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const remote = await ApiService.getSettings();
        if (remote.theme && remote.theme !== settings.theme) {
          updateSettings({
            theme: remote.theme as "light" | "dark" | "system",
          });
          setTheme(remote.theme);
        }
        if (remote.response_length) {
          updateSettings({
            responseLength:
              remote.response_length as "short" | "medium" | "detailed",
          });
        }
        if (remote.show_citations != null) {
          updateSettings({ showCitations: remote.show_citations });
        }
        if (remote.confidence_threshold != null) {
          updateSettings({ confidenceThreshold: remote.confidence_threshold });
        }
      } catch {
        // Backend may not be running — local defaults are fine
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // ── Save to backend ─────────────────────────────────────────────────────
  const handleSave = async () => {
    if (isSaving.current) return;
    isSaving.current = true;
    try {
      await ApiService.saveSettings({
        theme: (theme as "light" | "dark" | "system") ?? settings.theme,
        response_length: settings.responseLength,
        show_citations: settings.showCitations,
        confidence_threshold: settings.confidenceThreshold,
      });
      toast.success("Settings saved.");
      onOpenChange(false);
    } catch {
      toast.error(
        "Settings saved locally only — backend unavailable."
      );
      onOpenChange(false);
    } finally {
      isSaving.current = false;
    }
  };

  // ── Reset to defaults ───────────────────────────────────────────────────
  const handleReset = () => {
    updateSettings({
      theme: "dark",
      responseLength: "medium",
      showCitations: true,
      confidenceThreshold: 0.75,
    });
    setTheme("dark");
    toast.info("Settings reset to defaults.");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle className="text-xl">Settings</DialogTitle>
          <DialogDescription className="text-sm">
            Manage your preferences for the SecureHall-RAG portal.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {/* ── Theme ───────────────────────────────────────── */}
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-[15px] font-medium">Theme</h4>
              <p className="text-sm text-muted-foreground">
                Interface colour scheme
              </p>
            </div>
            <div className="flex gap-1.5">
              {(["light", "dark", "system"] as const).map((t) => (
                <Button
                  key={t}
                  variant={theme === t ? "default" : "outline"}
                  size="sm"
                  className="capitalize"
                  onClick={() => {
                    setTheme(t);
                    updateSettings({ theme: t });
                  }}
                >
                  {t}
                </Button>
              ))}
            </div>
          </div>

          {/* ── Response Length ──────────────────────────────── */}
          <div className="flex flex-col gap-2.5">
            <div>
              <h4 className="text-[15px] font-medium">Response Length</h4>
              <p className="text-sm text-muted-foreground">
                Preferred verbosity of answers
              </p>
            </div>
            <div className="flex gap-1.5 w-full">
              {(["short", "medium", "detailed"] as const).map((len) => (
                <Button
                  key={len}
                  variant={settings.responseLength === len ? "default" : "outline"}
                  size="sm"
                  className="flex-1 capitalize"
                  onClick={() => updateSettings({ responseLength: len })}
                >
                  {len}
                </Button>
              ))}
            </div>
          </div>

          {/* ── Show Citations ───────────────────────────────── */}
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-[15px] font-medium">Show Citations</h4>
              <p className="text-sm text-muted-foreground">
                Always include evidence sources
              </p>
            </div>
            <Button
              variant={settings.showCitations ? "default" : "outline"}
              size="sm"
              onClick={() =>
                updateSettings({ showCitations: !settings.showCitations })
              }
              className="min-w-[80px]"
            >
              {settings.showCitations ? "Enabled" : "Disabled"}
            </Button>
          </div>

          {/* ── Confidence Threshold ─────────────────────────── */}
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <div>
              <h4 className="text-[15px] font-medium">Confidence Threshold</h4>
                <p className="text-sm text-muted-foreground">
                  Minimum score for accepted answers
                </p>
              </div>
              <span className="text-sm font-semibold tabular-nums">
                {(settings.confidenceThreshold * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={settings.confidenceThreshold}
              onChange={(e) =>
                updateSettings({
                  confidenceThreshold: parseFloat(e.target.value),
                })
              }
              className="w-full accent-primary"
              aria-label="Confidence threshold"
              id="confidence-threshold-slider"
            />
            <div className="flex justify-between text-[10px] text-muted-foreground px-0.5">
              <span>Permissive (0%)</span>
              <span>Conservative (100%)</span>
            </div>
          </div>
        </div>

        {/* Footer actions */}
        <div className="flex gap-2 pt-2 border-t">
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 text-muted-foreground"
            onClick={handleReset}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </Button>
          <Button className="flex-1 gap-1.5" onClick={handleSave}>
            <Save className="h-3.5 w-3.5" />
            Save settings
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
