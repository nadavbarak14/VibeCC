import { useEffect } from "react";
import type { Project } from "../../types/api";
import { Button } from "../common/Button";

interface SettingsModalProps {
  project: Project;
  onClose: () => void;
}

export function SettingsModal({ project, onClose }: SettingsModalProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <>
      <div
        data-testid="settings-overlay"
        className="fixed inset-0 z-40 bg-black/30"
        onClick={onClose}
      />
      <div
        data-testid="settings-modal"
        className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-gray-200 bg-white shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Settings - {project.name}
          </h2>
          <button
            data-testid="settings-close-x"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            &#x2715;
          </button>
        </div>
        <div className="space-y-4 px-6 py-5">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-500">
              Base Branch
            </span>
            <span
              data-testid="setting-base-branch"
              className="text-sm text-gray-900"
            >
              {project.base_branch}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-500">
              Max CI Retries
            </span>
            <span
              data-testid="setting-max-ci"
              className="text-sm text-gray-900"
            >
              {project.max_retries_ci}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-500">
              Max Review Retries
            </span>
            <span
              data-testid="setting-max-review"
              className="text-sm text-gray-900"
            >
              {project.max_retries_review}
            </span>
          </div>
        </div>
        <div className="border-t border-gray-200 px-6 py-4">
          <Button
            data-testid="settings-close-btn"
            variant="secondary"
            onClick={onClose}
          >
            Close
          </Button>
        </div>
      </div>
    </>
  );
}
