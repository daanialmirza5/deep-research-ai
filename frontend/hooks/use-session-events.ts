"use client";

import { useEffect, useRef, useState } from "react";

import { getAccessToken } from "@/lib/auth";
import type { SessionEvent, SessionNodeUpdateEvent, SessionStatus } from "@/lib/types";

const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000/ws";

const TERMINAL_STATUSES = new Set(["completed", "failed"]);

interface SessionEventsState {
  status: SessionStatus | null;
  detail: string | null;
  nodeUpdates: SessionNodeUpdateEvent[];
}

// Subscribes to app/api/ws.py's /ws/sessions/{id}?token= relay: a live feed
// of {"type": "status", ...} / {"type": "node_update", ...} events published
// by the Celery worker as it streams the LangGraph pipeline. The socket
// closes itself server-side on a terminal status, so there's nothing to
// reconnect — only to tear down on unmount/session change.
//
// `initialStatus` is read once per `sessionId` via a ref rather than being a
// connection-effect dependency: it comes from a TanStack Query result that
// can refetch (and change identity) independently of the socket's own
// lifecycle, and re-running the connect effect on every such refetch would
// tear down and reopen the socket for no reason.
export function useSessionEvents(
  sessionId: string | null,
  initialStatus: SessionStatus | null,
): SessionEventsState {
  const [state, setState] = useState<SessionEventsState>({
    status: initialStatus,
    detail: null,
    nodeUpdates: [],
  });
  const initialStatusRef = useRef(initialStatus);
  useEffect(() => {
    initialStatusRef.current = initialStatus;
  });

  useEffect(() => {
    const startingStatus = initialStatusRef.current;
    setState({ status: startingStatus, detail: null, nodeUpdates: [] });

    if (!sessionId) return;
    // Nothing left to stream once a session already reached a terminal
    // state before this component ever mounted (e.g. viewing history).
    if (startingStatus === "completed" || startingStatus === "failed") return;

    const token = getAccessToken();
    if (!token) return;

    const socket = new WebSocket(
      `${WS_BASE_URL}/sessions/${sessionId}?token=${encodeURIComponent(token)}`,
    );

    socket.onmessage = (event) => {
      const parsed = JSON.parse(event.data) as SessionEvent;
      setState((prev) => {
        if (parsed.type === "status") {
          return { ...prev, status: parsed.status, detail: parsed.detail ?? null };
        }
        return { ...prev, nodeUpdates: [...prev.nodeUpdates, parsed] };
      });
    };

    return () => socket.close();
  }, [sessionId]);

  return state;
}

export function isTerminalStatus(status: SessionStatus | null): boolean {
  return status !== null && TERMINAL_STATUSES.has(status);
}
