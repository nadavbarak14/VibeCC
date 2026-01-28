import { useState, useCallback } from "react";
import { useSSE } from "./useSSE";
import type { LogEntry, SSEEvent, SSEStatus } from "../types/api";

interface UseLogStreamOptions {
  projectId: string;
  pipelineId: string;
  enabled?: boolean;
}

export function useLogStream({
  projectId,
  pipelineId,
  enabled = true,
}: UseLogStreamOptions): { logs: LogEntry[]; status: SSEStatus } {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const onEvent = useCallback(
    (event: SSEEvent) => {
      if (event.type === "log") {
        const data = event.data as unknown as LogEntry;
        if (data.pipeline_id === pipelineId) {
          setLogs((prev) => [...prev, data]);
        }
      }
    },
    [pipelineId],
  );

  const { status } = useSSE({ projectId, enabled, onEvent });

  return { logs, status };
}
