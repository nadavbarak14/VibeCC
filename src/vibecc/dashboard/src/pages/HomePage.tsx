import { useProjects } from "../hooks/useProjects";
import { ProjectGrid } from "../components/Projects/ProjectGrid";

export function HomePage() {
  const { data: projects, isLoading, error } = useProjects();

  if (isLoading) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-gray-500">Loading projects...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <h3 className="text-lg font-medium text-red-600">
          Failed to load projects
        </h3>
        <p className="mt-1 text-sm text-gray-500">{error.message}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
      </div>
      <ProjectGrid projects={projects ?? []} />
    </div>
  );
}
