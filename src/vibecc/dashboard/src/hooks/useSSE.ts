import { useEffect, useRef, useState, useCallback } from "react";
import type { SSEEvent, SSEEventType, SSEStatus } from "../types/api";

const SSE_URL = "/api/v1/events/stream";
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

const EVENT_TYPES: SSEEventType[] = [
  "pipeline_created",
  "pipeline_updated",
  "pipeline_completed",
  "log",
];

interface UseSSEOptions {
  projectId: string;
  enabled?: boolean;
  onEvent?: (event: SSEEvent) => void;
}

export function useSSE({
  projectId,
  enabled = true,
  onEvent,
}: UseSSEOptions): { status: SSEStatus } {
  const [status, setStatus] = useState<SSEStatus>("disconnected");
  const eventSourceRef = useRef<EventSource | null>(null);
  const onEventRef = useRef(onEvent);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);

  // Keep callback ref up to date without re-subscribing
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    const url = `${SSE_URL}?project_id=${projectId}`;
    setStatus("connecting");

    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setStatus("connected");
      reconnectAttemptRef.current = 0;
    };

    es.onerror = () => {
      es.close();
      eventSourceRef.current = null;
      setStatus("disconnected");

      // Auto-reconnect with exponential backoff
      const delay = Math.min(
        RECONNECT_BASE_MS * 2 ** reconnectAttemptRef.current,
        RECONNECT_MAX_MS,
      );
      reconnectAttemptRef.current += 1;
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, delay);
    };

    for (const eventType of EVENT_TYPES) {
      es.addEventListener(eventType, (event: MessageEvent) => {
        const data = JSON.parse(event.data) as Record<string, unknown>;
        onEventRef.current?.({ type: eventType, data });
      });
    }
  }, [projectId]);

  useEffect(() => {
    if (!enabled) {
      setStatus("disconnected");
      return;
    }

    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      reconnectAttemptRef.current = 0;
    };
  }, [projectId, enabled, connect]);

  return { status };
}
