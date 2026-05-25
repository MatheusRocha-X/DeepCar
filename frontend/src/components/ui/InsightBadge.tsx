import { cn, getInsightColor } from "@/lib/utils";
import { Sparkles } from "lucide-react";

interface InsightBadgeProps {
  insight: string;
  className?: string;
}

export function InsightBadge({ insight, className }: InsightBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-white/10 px-3 py-1 text-xs font-semibold backdrop-blur-xl",
        getInsightColor(insight),
        className
      )}
    >
      <Sparkles className="w-3 h-3 flex-shrink-0" />
      {insight}
    </span>
  );
}
