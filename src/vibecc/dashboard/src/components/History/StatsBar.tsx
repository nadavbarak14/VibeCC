import type { HistoryStats } from "../../types/api";

interface StatsBarProps {
  stats: HistoryStats;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

function successRate(stats: HistoryStats): string {
  if (stats.total_completed === 0) return "0%";
  return `${Math.round((stats.total_merged / stats.total_completed) * 100)}%`;
}

export function StatsBar({ stats }: StatsBarProps) {
  return (
    <div
      data-testid="stats-bar"
      className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4"
    >
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-sm text-gray-500">Total Completed</p>
        <p data-testid="stat-total" className="mt-1 text-2xl font-semibold text-gray-900">
          {stats.total_completed}
        </p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-sm text-gray-500">Success Rate</p>
        <p data-testid="stat-success-rate" className="mt-1 text-2xl font-semibold text-green-600">
          {successRate(stats)}
        </p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-sm text-gray-500">Avg Duration</p>
        <p data-testid="stat-avg-duration" className="mt-1 text-2xl font-semibold text-gray-900">
          {formatDuration(stats.avg_duration_seconds)}
        </p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-sm text-gray-500">Avg Retries</p>
        <p data-testid="stat-avg-retries" className="mt-1 text-2xl font-semibold text-gray-900">
          {stats.avg_retries_ci.toFixed(1)} CI / {stats.avg_retries_review.toFixed(1)} Review
        </p>
      </div>
    </div>
  );
}
