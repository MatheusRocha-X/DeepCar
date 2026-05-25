import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  const pages: (number | "...")[] = [];
  const delta = 2;

  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page - delta > 2) pages.push("...");
    for (let i = Math.max(2, page - delta); i <= Math.min(totalPages - 1, page + delta); i++) {
      pages.push(i);
    }
    if (page + delta < totalPages - 1) pages.push("...");
    pages.push(totalPages);
  }

  return (
    <nav className="surface-panel flex items-center justify-center gap-1 rounded-[1.7rem] px-3 py-3" aria-label="Paginação">
      <button
        onClick={() => onPageChange(1)}
        disabled={page === 1}
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-full transition-all",
          page === 1
            ? "cursor-not-allowed text-slate-600"
            : "secondary-button text-slate-300 hover:text-white"
        )}
        aria-label="Primeira página"
      >
        <ChevronsLeft className="w-4 h-4" />
      </button>
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-full transition-all",
          page === 1
            ? "cursor-not-allowed text-slate-600"
            : "secondary-button text-slate-300 hover:text-white"
        )}
        aria-label="Página anterior"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      {pages.map((p, i) =>
        p === "..." ? (
          <span key={`ellipsis-${i}`} className="px-2 text-sm text-slate-500">
            ...
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p as number)}
            className={cn(
              "h-10 w-10 rounded-full text-sm font-semibold transition-all",
              page === p
                ? "bg-gradient-to-br from-brand-400 to-brand-700 text-white shadow-[0_14px_30px_rgba(181,130,63,0.22)]"
                : "secondary-button text-slate-300 hover:text-white"
            )}
            aria-current={page === p ? "page" : undefined}
          >
            {p}
          </button>
        )
      )}

      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page === totalPages}
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-full transition-all",
          page === totalPages
            ? "cursor-not-allowed text-slate-600"
            : "secondary-button text-slate-300 hover:text-white"
        )}
        aria-label="Próxima página"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
      <button
        onClick={() => onPageChange(totalPages)}
        disabled={page === totalPages}
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-full transition-all",
          page === totalPages
            ? "cursor-not-allowed text-slate-600"
            : "secondary-button text-slate-300 hover:text-white"
        )}
        aria-label="Última página"
      >
        <ChevronsRight className="w-4 h-4" />
      </button>
    </nav>
  );
}
