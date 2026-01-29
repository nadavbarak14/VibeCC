interface SkeletonColumnProps {
  cardCount: number;
}

function SkeletonColumn({ cardCount }: SkeletonColumnProps) {
  return (
    <div className="flex min-w-[200px] flex-1 flex-col">
      {/* Header skeleton */}
      <div className="mb-3 flex items-center gap-2">
        <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-gray-300" />
        <div className="h-4 w-16 animate-pulse rounded bg-gray-300" />
        <div className="h-3 w-6 animate-pulse rounded bg-gray-200" />
      </div>

      {/* Column body */}
      <div className="flex-1 rounded-lg bg-gray-50 p-2">
        <div className="space-y-2">
          {Array.from({ length: cardCount }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
      {/* Ticket ID skeleton */}
      <div className="h-3 w-10 animate-pulse rounded bg-gray-200" />
      {/* Title skeleton - two lines */}
      <div className="mt-2 h-4 w-full animate-pulse rounded bg-gray-200" />
      <div className="mt-1 h-4 w-3/4 animate-pulse rounded bg-gray-200" />
      {/* State indicator skeleton */}
      <div className="mt-2 h-3 w-20 animate-pulse rounded bg-gray-200" />
    </div>
  );
}

export function KanbanSkeleton() {
  // Match the real board's 6 columns with varying card counts
  const columnCardCounts = [3, 2, 2, 3, 2, 1];

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {columnCardCounts.map((cardCount, index) => (
        <SkeletonColumn key={index} cardCount={cardCount} />
      ))}
    </div>
  );
}
