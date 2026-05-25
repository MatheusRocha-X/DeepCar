import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "skeleton rounded-[1rem] animate-pulse bg-white/5",
        className
      )}
    />
  );
}

export function VehicleCardSkeleton() {
  return (
    <div className="surface-card overflow-hidden rounded-[1.85rem]">
      <Skeleton className="w-full h-52" />
      <div className="p-4 space-y-3">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-8 w-2/5" />
        <div className="flex gap-1.5">
          <Skeleton className="h-7 w-20 rounded-md" />
          <Skeleton className="h-7 w-16 rounded-md" />
          <Skeleton className="h-7 w-14 rounded-md" />
        </div>
        <div className="flex gap-1.5 pt-1">
          <Skeleton className="h-5 w-24 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
        <div className="flex justify-between border-t border-white/10 pt-1">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-16" />
        </div>
      </div>
    </div>
  );
}
