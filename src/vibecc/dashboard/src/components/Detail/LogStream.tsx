import { useEffect, useRef } from "react";
import type { LogEntry } from "../../types/api";

interface LogStreamProps {
  logs: LogEntry[];
}

export function LogStream({ logs }: LogStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div data-testid="log-stream">
      <h4 className="mb-3 text-sm font-semibold text-gray-700">Live Logs</h4>
      <div className="max-h-60 overflow-y-auto rounded-lg bg-gray-900 p-3 font-mono text-xs text-gray-100">
        {logs.length === 0 ? (
          <p className="text-gray-500">Waiting for logs...</p>
        ) : (
          logs.map((log, i) => (
            <div key={i} className="py-0.5" data-testid="log-entry">
              <span className="text-gray-500">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>{" "}
              <span
                className={
                  log.level === "error"
                    ? "text-red-400"
                    : log.level === "warning"
                      ? "text-yellow-400"
                      : "text-gray-100"
                }
              >
                {log.message}
              </span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
