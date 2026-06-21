/**
 * useHealthCheck — Phase 5B.3 (Frontend Project Setup)
 *
 * Polls the backend /health endpoint every 30 seconds.
 * Uses native fetch() with an AbortController timeout instead of the
 * ApiService Axios client, so the Axios error interceptor does NOT
 * interfere — a network failure simply sets status="offline" instead
 * of throwing a normalised error through the whole stack.
 */
"use client";

import { useState, useEffect, useCallback, useRef } from "react";

export type BackendStatus = "checking" | "online" | "offline" | "no_documents";

interface HealthResponse {
  status: string;
  pipeline?: {
    initialized: boolean;
    index_ready: boolean;
    status: string;
  };
}

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

// Health endpoint is at /api/v1/health (aliased in main.py)
const HEALTH_URL = `${BASE_URL}/health`;

export function useHealthCheck(pollIntervalMs = 30_000) {
  const [status, setStatus] = useState<BackendStatus>("checking");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const check = useCallback(async () => {
    // Use a 5-second timeout — much shorter than the Axios default (2 min)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5_000);

    try {
      const res = await fetch(HEALTH_URL, {
        method: "GET",
        signal: controller.signal,
        // Avoid CORS preflight by only sending simple headers
        headers: { Accept: "application/json" },
        // No credentials needed for the health endpoint
        credentials: "omit",
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        setStatus("offline");
        return;
      }

      const data: HealthResponse = await res.json();

      // Check if pipeline has indexed documents
      if (data.pipeline && !data.pipeline.index_ready) {
        setStatus("no_documents");
      } else {
        setStatus("online");
      }
    } catch {
      clearTimeout(timeoutId);
      // AbortError (timeout) or network error — mark as offline
      setStatus("offline");
    }
  }, []);

  useEffect(() => {
    void check();
    timerRef.current = setInterval(() => void check(), pollIntervalMs);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [check, pollIntervalMs]);

  return { status, refresh: check };
}
