import type { PipelineHistory } from "../../types/api";
import { Badge } from "../common/Badge";

interface HistoryTableProps {
  items: PipelineHistory[];
  page: number;
  onPageChange: (page: number) => void;
  hasMore: boolean;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function HistoryTable({
  items,
  page,
  onPageChange,
  hasMore,
}: HistoryTableProps) {
  if (items.length === 0) {
    return (
      <div data-testid="history-empty" className="py-12 text-center">
        <p className="text-sm text-gray-500">No history to show.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Ticket
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Duration
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Retries
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Completed
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {items.map((item) => (
              <tr key={item.id} data-testid={`history-row-${item.id}`}>
                <td className="px-4 py-3">
                  <span className="font-medium text-gray-900">
                    #{item.ticket_id}
                  </span>{" "}
                  <span className="text-gray-600">{item.ticket_title}</span>
                </td>
                <td className="px-4 py-3">
                  <Badge
                    label={item.final_state}
                    color={item.final_state === "merged" ? "green" : "red"}
                  />
                </td>
                <td
                  className="px-4 py-3 text-sm text-gray-600"
                  data-testid={`duration-${item.id}`}
                >
                  {formatDuration(item.duration_seconds)}
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">
                  CI {item.total_retries_ci} / Review {item.total_retries_review}
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">
                  {formatDate(item.completed_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex items-center justify-between">
        <button
          data-testid="page-prev"
          onClick={() => onPageChange(page - 1)}
          disabled={page === 0}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Previous
        </button>
        <span data-testid="page-info" className="text-sm text-gray-500">
          Page {page + 1}
        </span>
        <button
          data-testid="page-next"
          onClick={() => onPageChange(page + 1)}
          disabled={!hasMore}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
