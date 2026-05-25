import { cn } from "@/lib/utils";
import { getScoreColor, getScoreLabel } from "@/lib/utils";

interface ScoreRingProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

export function ScoreRing({ score, size = "md", showLabel = false, className }: ScoreRingProps) {
  const radius = size === "sm" ? 16 : size === "md" ? 22 : 30;
  const stroke = size === "sm" ? 3 : size === "md" ? 4 : 5;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const svgSize = (radius + stroke) * 2;

  const colorClass = getScoreColor(score);
  const strokeColors: Record<string, string> = {
    "text-green-500": "#22c55e",
    "text-emerald-400": "#2dd4bf",
    "text-yellow-500": "#facc15",
    "text-orange-500": "#fb923c",
    "text-red-500": "#f87171",
  };
  const strokeColor = strokeColors[colorClass] || "#b5823f";

  const fontSize = size === "sm" ? "text-xs" : size === "md" ? "text-sm" : "text-base";

  return (
    <div className={cn("flex flex-col items-center gap-0.5", className)}>
      <div className="relative inline-flex items-center justify-center rounded-full bg-white/5">
        <svg width={svgSize} height={svgSize} className="-rotate-90 drop-shadow-[0_0_12px_rgba(199,160,102,0.16)]">
          <circle
            cx={svgSize / 2}
            cy={svgSize / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={stroke}
            className="text-slate-300/25 dark:text-white/10"
          />
          <circle
            cx={svgSize / 2}
            cy={svgSize / 2}
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <span
          className={cn(
            "absolute font-bold tabular-nums",
            fontSize,
            "text-slate-900 dark:text-white"
          )}
        >
          {Math.round(score)}
        </span>
      </div>
      {showLabel && (
        <span className={cn("text-xs font-medium", colorClass)}>
          {getScoreLabel(score)}
        </span>
      )}
    </div>
  );
}
