"use client";

import { useSearchStore } from "@/store";
import type { OrderBy } from "@/types";
import { cn } from "@/lib/utils";
import { TrendingUp, DollarSign, Gauge, Clock, ArrowUpDown } from "lucide-react";

const ORDER_OPTIONS: { value: OrderBy; label: string; icon: React.ReactNode }[] = [
  { value: "score", label: "Melhor Score", icon: <TrendingUp className="w-3.5 h-3.5" /> },
  { value: "menor_preco", label: "Menor Preço", icon: <DollarSign className="w-3.5 h-3.5" /> },
  { value: "maior_preco", label: "Maior Preço", icon: <DollarSign className="w-3.5 h-3.5" /> },
  { value: "menor_km", label: "Menor KM", icon: <Gauge className="w-3.5 h-3.5" /> },
  { value: "mais_recente", label: "Mais Recente", icon: <Clock className="w-3.5 h-3.5" /> },
];

interface SortBarProps {
  total: number;
  isLoading?: boolean;
}

export function SortBar({ total, isLoading }: SortBarProps) {
  const { filters, setOrderBy } = useSearchStore();

  return (
    <div className="surface-panel rounded-[1.6rem] px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <p className="text-[0.62rem] font-semibold uppercase tracking-[0.32em] text-brand-200/70">
            Catálogo vivo
          </p>
          <div className="mt-2 text-sm text-slate-400">
            {isLoading ? (
              <span className="inline-block h-4 w-32 rounded-full skeleton" />
            ) : (
              <>
                <strong className="text-slate-900 dark:text-white">
                  {total.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".")}
                </strong>{" "}
                {total === 1 ? "veículo encontrado" : "veículos encontrados"}
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide pb-1 lg:pb-0">
          <ArrowUpDown className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" />
          {ORDER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setOrderBy(opt.value)}
              className={cn(
                "flex flex-shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-2 text-xs font-semibold whitespace-nowrap transition-all",
                filters.order_by === opt.value
                  ? "border-brand-400/40 bg-brand-500/15 text-white shadow-[0_10px_24px_rgba(181,130,63,0.16)]"
                  : "border-white/[0.06] bg-white/[0.03] text-slate-300 hover:border-white/[0.08] hover:bg-white/[0.04] hover:text-white"
              )}
            >
              {opt.icon}
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
