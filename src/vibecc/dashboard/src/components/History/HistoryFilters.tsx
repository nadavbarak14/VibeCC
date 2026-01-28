interface HistoryFiltersProps {
  value: "all" | "merged" | "failed";
  onChange: (value: "all" | "merged" | "failed") => void;
}

const options = [
  { value: "all" as const, label: "All" },
  { value: "merged" as const, label: "Merged" },
  { value: "failed" as const, label: "Failed" },
];

export function HistoryFilters({ value, onChange }: HistoryFiltersProps) {
  return (
    <div data-testid="history-filters" className="mb-4 flex items-center gap-2">
      <span className="text-sm font-medium text-gray-700">Status:</span>
      <div className="flex rounded-lg border border-gray-200 bg-white">
        {options.map((opt) => (
          <button
            key={opt.value}
            data-testid={`filter-${opt.value}`}
            onClick={() => onChange(opt.value)}
            className={`px-3 py-1.5 text-sm font-medium transition-colors ${
              value === opt.value
                ? "bg-gray-900 text-white"
                : "text-gray-600 hover:bg-gray-100"
            } ${opt.value === "all" ? "rounded-l-lg" : ""} ${opt.value === "failed" ? "rounded-r-lg" : ""}`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
