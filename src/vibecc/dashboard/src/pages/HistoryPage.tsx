import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useProject } from "../hooks/useProject";
import { useHistory } from "../hooks/useHistory";
import { useHistoryStats } from "../hooks/useHistoryStats";
import { StatsBar } from "../components/History/StatsBar";
import { HistoryFilters } from "../components/History/HistoryFilters";
import { HistoryTable } from "../components/History/HistoryTable";
import type { HistoryFilters as HistoryFiltersType } from "../types/api";

const PAGE_SIZE = 50;

export function HistoryPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [statusFilter, setStatusFilter] = useState<"all" | "merged" | "failed">(
    "all",
  );
  const [page, setPage] = useState(0);

  const filters: HistoryFiltersType = {
    final_state: statusFilter === "all" ? undefined : statusFilter,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  };

  const { data: project, isLoading: projectLoading } = useProject(projectId!);
  const { data: history, isLoading: historyLoading } = useHistory(
    projectId!,
    filters,
  );
  const { data: stats } = useHistoryStats(projectId!);

  const handleFilterChange = (value: "all" | "merged" | "failed") => {
    setStatusFilter(value);
    setPage(0);
  };

  if (projectLoading || historyLoading) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-gray-500">Loading history...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="py-12 text-center">
        <h3 className="text-lg font-medium text-red-600">Project not found</h3>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <Link
              to={`/projects/${projectId}`}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              {project.name}
            </Link>
            <span className="text-sm text-gray-400">/</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">History</h1>
        </div>
      </div>

      {stats && <StatsBar stats={stats} />}

      <HistoryFilters value={statusFilter} onChange={handleFilterChange} />

      <HistoryTable
        items={history ?? []}
        page={page}
        onPageChange={setPage}
        hasMore={(history?.length ?? 0) === PAGE_SIZE}
      />
    </div>
  );
}
