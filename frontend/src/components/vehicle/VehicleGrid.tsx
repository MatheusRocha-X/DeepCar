"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  cancelQueryScrape,
  getInitialBootstrapStatus,
  getSearchScrapeProgress,
  searchVehicles,
  openLiveScrapeStream,
} from "@/lib/api";
import { useSearchStore } from "@/store";
import { cn } from "@/lib/utils";
import { VehicleCard } from "./VehicleCard";
import { VehicleCardSkeleton } from "@/components/ui/Skeleton";
import { SortBar } from "@/components/search/SortBar";
import { Pagination } from "@/components/ui/Pagination";
import type { SearchFilters } from "@/types";
import { Car, SearchX, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

function formatQueryNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : String(value);
}

function buildSmartQuery(filters: SearchFilters): string {
  if (!hasAppliedSearchFilters(filters)) {
    return "";
  }

  const q = filters.q?.trim() || "";
  const marca = filters.marca?.trim() || "";
  const modelo = filters.modelo?.trim() || "";
  const combustivel = filters.combustivel?.trim() || "";
  const cambio = filters.cambio?.trim() || "";
  const vendedorTipo = filters.vendedor_tipo?.trim() || "";
  const cidade = filters.cidade?.trim() || "";
  const estado = filters.estado?.trim() || "";
  const source = filters.source?.trim() || "";
  const parts: string[] = [];

  if (q) {
    parts.push(q);
    if (marca) {
      parts.push(`marca ${marca}`);
    }
    if (modelo) {
      parts.push(`modelo ${modelo}`);
    }
  } else {
    if (marca) {
      parts.push(marca);
    }
    if (modelo) {
      parts.push(modelo);
    }
    if (!parts.length) {
      parts.push("carro");
    }
  }

  if (combustivel) {
    parts.push(`combustivel ${combustivel}`);
  }
  if (cambio) {
    parts.push(`cambio ${cambio}`);
  }
  if (vendedorTipo) {
    parts.push(`vendedor ${vendedorTipo}`);
  }
  if (cidade) {
    parts.push(`cidade ${cidade}`);
  }
  if (estado) {
    parts.push(`estado ${estado}`);
  }

  if (filters.ano_min !== undefined && filters.ano_max !== undefined) {
    parts.push(`ano ${filters.ano_min}-${filters.ano_max}`);
  } else if (filters.ano_min !== undefined) {
    parts.push(`ano ${filters.ano_min}+`);
  } else if (filters.ano_max !== undefined) {
    parts.push(`ano ate ${filters.ano_max}`);
  }

  if (filters.km_min !== undefined && filters.km_max !== undefined) {
    parts.push(`km ${filters.km_min}-${filters.km_max}`);
  } else if (filters.km_min !== undefined) {
    parts.push(`km ${filters.km_min}+`);
  } else if (filters.km_max !== undefined) {
    parts.push(`km ate ${filters.km_max}`);
  }

  if (filters.preco_min !== undefined && filters.preco_max !== undefined) {
    parts.push(`preco ${formatQueryNumber(filters.preco_min)}-${formatQueryNumber(filters.preco_max)}`);
  } else if (filters.preco_min !== undefined) {
    parts.push(`preco ${formatQueryNumber(filters.preco_min)}+`);
  } else if (filters.preco_max !== undefined) {
    parts.push(`preco ate ${formatQueryNumber(filters.preco_max)}`);
  }

  if (source) {
    parts.push(`fonte ${source}`);
  }

  return parts.join(" ");
}

function hasAppliedSearchFilters(filters: SearchFilters): boolean {
  return Object.entries(filters).some(([key, value]) => {
    if (key === "order_by" || key === "page" || key === "per_page") {
      return false;
    }

    return value !== undefined && value !== null && value !== "";
  });
}

export function VehicleGrid() {
  const { filters, setPage, hasHydrated } = useSearchStore();
  const queryClient = useQueryClient();
  const [liveStatus, setLiveStatus] = useState<"idle" | "searching" | "done">("idle");
  const [backgroundRefreshUntil, setBackgroundRefreshUntil] = useState<number | null>(null);
  const liveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastLiveQuery = useRef<string>("");
  const activeSearchQuery = useRef<string>("");
  const streamCleanupRef = useRef<(() => void) | null>(null);
  const smartQuery = buildSmartQuery(filters);
  const isDefaultCatalogView = !hasAppliedSearchFilters(filters);
  const shouldPollSmartSearchProgress = smartQuery.length >= 3
    && Boolean(backgroundRefreshUntil && Date.now() < backgroundRefreshUntil);

  const { data: bootstrapStatus } = useQuery({
    queryKey: ["initialBootstrapStatus"],
    queryFn: getInitialBootstrapStatus,
    refetchInterval: (query) => {
      const status = query.state.data;
      if (isDefaultCatalogView && (!status || (!status.done && status.status !== "skipped"))) {
        return 1500;
      }

      return status?.running ? 1500 : false;
    },
    refetchIntervalInBackground: true,
    staleTime: 0,
  });

  const { data: scrapeProgress } = useQuery({
    queryKey: ["scrapeProgress", smartQuery],
    queryFn: () => getSearchScrapeProgress(smartQuery),
    enabled: hasHydrated && smartQuery.length >= 3,
    refetchInterval: (query) => {
      const progress = query.state.data;
      if (progress?.done) {
        return false;
      }

      return progress?.running || shouldPollSmartSearchProgress ? 1500 : false;
    },
    refetchIntervalInBackground: true,
    staleTime: 0,
  });

  const isScrapeRunning = Boolean(scrapeProgress?.running);
  const pagesScraped = scrapeProgress?.pages_scraped ?? 0;
  const minPagesBeforeDisplay = scrapeProgress?.min_pages_before_display ?? 3;
  const isOlxWorkerOnlySearch = Boolean(
    scrapeProgress?.worker_running && !scrapeProgress?.task_running && pagesScraped === 0
  );

  const { data, isLoading, isFetching, isError } = useQuery({
    queryKey: ["vehicles", filters],
    queryFn: () => searchVehicles(filters),
    enabled: hasHydrated,
    placeholderData: (prev) => prev,
    refetchInterval: () =>
      isScrapeRunning || (backgroundRefreshUntil && Date.now() < backgroundRefreshUntil)
        || (isDefaultCatalogView && Boolean(!bootstrapStatus?.done || bootstrapStatus?.running))
        ? 3000
        : false,
    refetchIntervalInBackground: true,
  });

  const hasResults = (data?.results.length ?? 0) > 0;
  // Only hold back the grid while we have zero DB results yet — once the DB
  // already returned matches, show them immediately and keep scraping in bg.
  const shouldDeferReveal = smartQuery.length >= 3 && !hasResults && !scrapeProgress?.display_ready && !scrapeProgress?.done;
  const hasVisibleResults = hasResults && !shouldDeferReveal;
  const totalResults = data?.total ?? 0;
  const totalResultPages = data?.total_pages ?? 0;
  const isSmartSearchActive = smartQuery.length >= 3
    && !scrapeProgress?.done
    && (shouldDeferReveal || isScrapeRunning || liveStatus === "searching" || isFetching);
  const shouldHoldEmptyState = isSmartSearchActive && !hasVisibleResults && pagesScraped < minPagesBeforeDisplay;
  const showSearchingBanner = isSmartSearchActive;
  const showPendingSearchEmptyState = smartQuery.length >= 3 && !hasVisibleResults && !scrapeProgress?.done;
  const showInitialBootstrapBanner = isDefaultCatalogView && Boolean(bootstrapStatus?.running);
  const showInitialBootstrapEmptyState = showInitialBootstrapBanner && !hasResults;
  const bootstrapTargets = bootstrapStatus?.targets ?? { olx: 500 };
  const bootstrapTotalTarget = bootstrapStatus?.total_target ?? Object.values(bootstrapTargets).reduce((sum, target) => sum + target, 0);
  const bootstrapTotalSaved = Math.min(bootstrapStatus?.total_saved ?? 0, bootstrapTotalTarget);
  const showHydrationLoadingState = !hasHydrated;

  useEffect(() => {
    const previousQuery = activeSearchQuery.current;
    if (previousQuery && previousQuery !== smartQuery) {
      void cancelQueryScrape(previousQuery).catch(() => {
        // Ignore cancellation errors — the UI should still clear immediately.
      });
    }

    activeSearchQuery.current = smartQuery;

    if (!smartQuery) {
      setBackgroundRefreshUntil(null);
      setLiveStatus("idle");
      lastLiveQuery.current = "";
    }
  }, [smartQuery]);

  useEffect(() => {
    if (smartQuery.length < 3) {
      setBackgroundRefreshUntil(null);
      lastLiveQuery.current = "";
      return;
    }

    // Mark polling as active for this search. Uses MAX_SAFE_INTEGER so the
    // Date.now() < backgroundRefreshUntil checks never expire on their own —
    // polling continues until scrapeProgress.done fires or the filter is cleared.
    setBackgroundRefreshUntil(Number.MAX_SAFE_INTEGER);
  }, [smartQuery]);

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    const shouldPulseSmartSearch = smartQuery.length >= 3 && Boolean(backgroundRefreshUntil && Date.now() < backgroundRefreshUntil);
    const shouldPulseBootstrap = isDefaultCatalogView && Boolean(!bootstrapStatus?.done || bootstrapStatus?.running);

    if (!shouldPulseSmartSearch && !shouldPulseBootstrap) {
      return;
    }

    const interval = window.setInterval(() => {
      if (shouldPulseBootstrap) {
        queryClient.invalidateQueries({ queryKey: ["initialBootstrapStatus"] });
      }

      if (shouldPulseSmartSearch) {
        queryClient.invalidateQueries({ queryKey: ["scrapeProgress", smartQuery] });
      }

      if (shouldPulseSmartSearch || shouldPulseBootstrap) {
        queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      }
    }, shouldPulseSmartSearch ? 1500 : 3000);

    return () => window.clearInterval(interval);
  }, [
    backgroundRefreshUntil,
    bootstrapStatus?.done,
    bootstrapStatus?.running,
    hasHydrated,
    isDefaultCatalogView,
    queryClient,
    smartQuery,
  ]);

  useEffect(() => {
    if (scrapeProgress?.display_ready) {
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    }

    if (scrapeProgress?.done) {
      setBackgroundRefreshUntil(null);
    }
  }, [scrapeProgress?.display_ready, scrapeProgress?.done, queryClient]);

  useEffect(() => {
    if (!isDefaultCatalogView || !bootstrapStatus?.done) {
      return;
    }

    queryClient.invalidateQueries({ queryKey: ["vehicles"] });
  }, [bootstrapStatus?.done, isDefaultCatalogView, queryClient]);

  useEffect(() => {
    if (!backgroundRefreshUntil) return;
    // Only clear early when the scrape is definitively done AND we already
    // have results. Do NOT clear on isScrapeRunning=false alone — the first
    // /progress response can be idle before the worker has even confirmed
    // it started, which was causing premature polling termination.
    if ((data?.total ?? 0) > 0 && scrapeProgress?.done) {
      setBackgroundRefreshUntil(null);
    }
  }, [backgroundRefreshUntil, data?.total, scrapeProgress?.done]);

  // Trigger real-time live scrape via SSE when user has a text query
  useEffect(() => {
    if (smartQuery.length < 3) return;
    if (smartQuery === lastLiveQuery.current) return;

    // Debounce: wait 800ms after the query stabilises before opening the stream
    if (liveTimerRef.current) clearTimeout(liveTimerRef.current);
    liveTimerRef.current = setTimeout(() => {
      lastLiveQuery.current = smartQuery;
      // Close any existing stream before opening a new one
      streamCleanupRef.current?.();
      setLiveStatus("searching");

      const cleanup = openLiveScrapeStream(
        smartQuery,
        (_data) => {
          // New vehicles arrived — refresh results immediately
          queryClient.invalidateQueries({ queryKey: ["vehicles"] });
        },
        (total) => {
          // Always refresh after stream ends to show latest DB results
          queryClient.invalidateQueries({ queryKey: ["vehicles"] });
          if (total > 0) {
            setLiveStatus("done");
            setTimeout(() => setLiveStatus("idle"), 3000);
          } else {
            setLiveStatus("idle");
          }
          streamCleanupRef.current = null;
        }
      );
      streamCleanupRef.current = cleanup;
    }, 800);

    return () => {
      if (liveTimerRef.current) clearTimeout(liveTimerRef.current);
      streamCleanupRef.current?.();
      streamCleanupRef.current = null;
    };
  }, [smartQuery, queryClient]);

  function handlePageChange(page: number) {
    setPage(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="space-y-5">
      <SortBar total={data?.total || 0} isLoading={isLoading} />

      {showSearchingBanner ? (
        <div className={`flex items-center gap-2 rounded-[1.6rem] border px-4 py-3 text-sm leading-relaxed ${
          hasVisibleResults
            ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-50"
            : "border-brand-400/25 bg-brand-500/12 text-slate-100"
        }`}>
          {hasVisibleResults && isOlxWorkerOnlySearch ? (
            <>
              <span className="h-2 w-2 rounded-full bg-emerald-400 flex-shrink-0" />
              Pesquisando mais opções para &ldquo;{smartQuery}&rdquo; na OLX. Já encontramos {totalResults} anúncio{totalResults === 1 ? "" : "s"} em {totalResultPages || 1} página{(totalResultPages || 1) === 1 ? "" : "s"} de resultado.
            </>
          ) : hasVisibleResults ? (
            <>
              <span className="h-2 w-2 rounded-full bg-emerald-400 flex-shrink-0" />
              Pesquisando mais opções para &ldquo;{smartQuery}&rdquo;. Já analisamos {pagesScraped} página{pagesScraped === 1 ? "" : "s"} dos sites e, por enquanto, encontramos {totalResults} anúncio{totalResults === 1 ? "" : "s"} em {totalResultPages || 1} página{(totalResultPages || 1) === 1 ? "" : "s"} de resultado.
            </>
          ) : isOlxWorkerOnlySearch ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin flex-shrink-0 text-brand-300" />
              Pesquisando &ldquo;{smartQuery}&rdquo;. Assim que os primeiros anúncios forem encontrados, os resultados aparecem aqui automaticamente.
            </>
          ) : pagesScraped >= minPagesBeforeDisplay ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin flex-shrink-0 text-brand-300" />
              Já analisamos {pagesScraped} página{pagesScraped === 1 ? "" : "s"} dos sites para &ldquo;{smartQuery}&rdquo;, mas ainda não encontramos anúncios que batam com esses filtros.
            </>
          ) : (
            <>
              <Loader2 className="h-4 w-4 animate-spin flex-shrink-0 text-brand-300" />
              Pesquisando &ldquo;{smartQuery}&rdquo;. {pagesScraped}/{minPagesBeforeDisplay} páginas dos sites analisadas antes de liberar os primeiros resultados.
            </>
          )}
        </div>
      ) : liveStatus !== "idle" ? (
        <div className="flex items-center gap-2 rounded-[1.6rem] border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-50">
          <span className="h-2 w-2 rounded-full bg-emerald-400 flex-shrink-0" />
          Novos anúncios encontrados!
        </div>
      ) : null}

      {showInitialBootstrapBanner ? (
        <div className="flex flex-col gap-3 rounded-[1.8rem] border border-amber-400/20 bg-amber-500/10 px-4 py-4 text-amber-50 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-white/10 text-amber-200">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
            <div>
              <p className="text-sm font-semibold">A DeepCar está iniciando sua base inicial</p>
              <p className="text-sm text-amber-100/80">
                Estamos carregando os anúncios iniciais para liberar a primeira experiência.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 text-xs font-medium">
            <span className="rounded-full border border-amber-300/20 bg-white/10 px-3 py-1 text-amber-100">
              {bootstrapTotalSaved}/{bootstrapTotalTarget} anúncios
            </span>
          </div>
        </div>
      ) : null}

      {isError && (
        <div className="surface-panel flex flex-col items-center justify-center rounded-[2rem] px-6 py-16 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-[1.6rem] bg-rose-500/15">
            <SearchX className="h-8 w-8 text-rose-300" />
          </div>
          <h3 className="mb-1 text-lg font-semibold text-slate-900 dark:text-white">
            Erro ao carregar veículos
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Verifique sua conexão e tente novamente.
          </p>
        </div>
      )}

      {showHydrationLoadingState ? (
        <div className="surface-panel flex flex-col items-center justify-center rounded-[2rem] px-6 py-16 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-[1.6rem] bg-brand-500/15">
            <Loader2 className="h-8 w-8 animate-spin text-brand-300" />
          </div>
          <h3 className="mb-1 text-lg font-semibold text-slate-900 dark:text-white">
            Restaurando sua busca
          </h3>
          <p className="max-w-md text-sm text-slate-500 dark:text-slate-400">
            Estamos recuperando os filtros e o carregamento anterior para que o refresh não interrompa sua experiência.
          </p>
        </div>
      ) : isLoading || shouldHoldEmptyState ? (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {[...Array(9)].map((_, i) => (
            <VehicleCardSkeleton key={i} />
          ))}
        </div>
      ) : !hasVisibleResults ? (
        showInitialBootstrapEmptyState ? (
          <div className="surface-panel flex flex-col items-center justify-center rounded-[2rem] border border-dashed border-amber-400/20 px-6 py-16 text-center">
            <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-3xl bg-amber-500/10 text-amber-200">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
            <h3 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">
              Estamos preparando a DeepCar para você
            </h3>
            <p className="max-w-xl text-sm leading-relaxed text-slate-500 dark:text-slate-400">
              Nesta primeira abertura, estamos carregando os anúncios iniciais. Assim que os primeiros lotes terminarem, os veículos começam a aparecer aqui automaticamente.
            </p>

            <div className="mt-6 flex flex-wrap justify-center gap-3 text-sm font-medium">
              <span className="rounded-full border border-amber-400/20 bg-amber-500/10 px-4 py-2 text-amber-100">
                {bootstrapTotalSaved}/{bootstrapTotalTarget} anúncios
              </span>
            </div>

            <p className="mt-4 text-xs uppercase tracking-[0.24em] text-amber-100/70">
              Carregando a base inicial de {bootstrapTotalTarget.toLocaleString("pt-BR")} anúncios
            </p>
          </div>
        ) : showPendingSearchEmptyState ? (
          <div className="surface-panel flex flex-col items-center justify-center rounded-[2rem] px-6 py-16 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-[1.6rem] bg-brand-500/15">
              <Loader2 className="h-8 w-8 animate-spin text-brand-300" />
            </div>
            <h3 className="mb-1 text-lg font-semibold text-slate-900 dark:text-white">
              Ainda pesquisando esse carro
            </h3>
            <p className="max-w-md text-sm text-slate-500 dark:text-slate-400">
              {pagesScraped > 0
                ? `Já analisamos ${pagesScraped} página${pagesScraped === 1 ? "" : "s"} dos sites para “${smartQuery}”, mas a busca ainda não terminou.`
                : `Estamos buscando os primeiros anúncios para “${smartQuery}”. Assim que as páginas iniciais terminarem, os resultados aparecem aqui automaticamente.`}
            </p>
          </div>
        ) : (
          <div className="surface-panel flex flex-col items-center justify-center rounded-[2rem] px-6 py-16 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-[1.6rem] bg-white/5">
              <Car className="h-8 w-8 text-slate-500" />
            </div>
            <h3 className="mb-1 text-lg font-semibold text-slate-900 dark:text-white">
              Nenhum veículo encontrado
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Tente ajustar os filtros para ver mais resultados.
            </p>
          </div>
        )
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {data?.results.map((vehicle, i) => (
            <VehicleCard key={vehicle.id} vehicle={vehicle} index={i} />
          ))}
        </div>
      )}

      {data && data.total_pages > 1 && (
        <Pagination
          page={filters.page || 1}
          totalPages={data.total_pages}
          onPageChange={handlePageChange}
        />
      )}
    </div>
  );
}
