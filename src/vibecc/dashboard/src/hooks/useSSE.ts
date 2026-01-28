import { useEffect, useRef, useState } from "react";
import type { LogEntry } from "../types/api";

const SSE_URL = "/api/v1/events/stream";

interface UseSSEOptions {
  projectId: string;
  pipelineId: string;
  enabled?: boolean;
}

export function useSSE({ projectId, pipelineId, enabled = true }: UseSSEOptions) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const url = `${SSE_URL}?project_id=${projectId}`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.addEventListener("log", (event) => {
      const data = JSON.parse(event.data) as LogEntry;
      if (data.pipeline_id === pipelineId) {
        setLogs((prev) => [...prev, data]);
      }
    });

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [projectId, pipelineId, enabled]);

  return { logs };
}
