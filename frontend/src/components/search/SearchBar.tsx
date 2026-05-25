"use client";

import { Search, X } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { useSearchStore } from "@/store";
import { cn } from "@/lib/utils";

export function SearchBar() {
  const { filters, setFilters } = useSearchStore();
  const [localQ, setLocalQ] = useState(filters.q || "");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setLocalQ(filters.q || "");
  }, [filters.q]);

  function applySearch(value: string) {
    setFilters({ q: value || undefined });
  }

  function handleChange(value: string) {
    setLocalQ(value);
  }

  function handleClear() {
    setLocalQ("");
    applySearch("");
    inputRef.current?.focus();
  }

  return (
    <div className="rounded-[1.9rem]">
      <div className="flex flex-col gap-3 lg:flex-row">
        <div className="input-shell relative flex-1 rounded-[1.55rem] px-4">
          <div className="absolute left-4 top-1/2 -translate-y-1/2">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-500/15 text-brand-300">
              <Search className="h-5 w-5" />
            </div>
          </div>

          <div className="pl-14 pr-10">
            <span className="pt-3 text-[0.62rem] font-semibold uppercase tracking-[0.32em] text-slate-400 sm:block">
              Sua busca
            </span>
            <input
              ref={inputRef}
              type="text"
              value={localQ}
              onChange={(e) => handleChange(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && applySearch(localQ)}
              placeholder="Ex.: Corolla XEi 2022 em Curitiba"
              className={cn(
                "w-full bg-transparent pb-3 pt-1 text-base text-slate-900 outline-none transition-colors dark:text-white",
                "placeholder:text-slate-400 dark:placeholder:text-slate-500"
              )}
            />
          </div>

          {localQ && (
            <button
              onClick={handleClear}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
              aria-label="Limpar busca"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        <button
          onClick={() => applySearch(localQ)}
          className="primary-button whitespace-nowrap rounded-[1.55rem] px-6 py-4 text-sm font-semibold transition-all"
        >
          Analisar anúncios
        </button>
      </div>

      <p className="px-1 pt-3 text-xs leading-relaxed text-slate-400">
        Combine modelo, versão, cidade, ano e preço numa leitura única de mercado.
      </p>
    </div>
  );
}
