"use client";

import * as SelectPrimitive from "@radix-ui/react-select";
import { useIsFetching, useQuery } from "@tanstack/react-query";
import { getFilterOptions, getInitialBootstrapStatus, getSearchScrapeProgress } from "@/lib/api";
import { useSearchStore } from "@/store";
import type { SearchFilters } from "@/types";
import { cn } from "@/lib/utils";
import { SlidersHorizontal, ChevronDown, X, Search, Check, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";

const EMPTY_SELECT_VALUE = "__deepcar_any__";

/** Input de texto que exibe números formatados com separador pt-BR (ex: 20.000). */
function NumInput({
  value,
  onChange,
  placeholder,
}: {
  value?: number;
  onChange: (v: number | undefined) => void;
  placeholder: string;
}) {
  const fmt = (n: number) =>
    n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");

  const [display, setDisplay] = useState(value !== undefined ? fmt(value) : "");

  // Sincroniza quando o valor externo muda (ex: reset)
  useEffect(() => {
    setDisplay(value !== undefined ? fmt(value) : "");
  }, [value]);

  return (
    <input
      type="text"
      inputMode="numeric"
      placeholder={placeholder}
      value={display}
      onChange={(e) => {
        const raw = e.target.value.replace(/\D/g, "");
        const num = raw ? Number(raw) : undefined;
        setDisplay(raw ? fmt(Number(raw)) : "");
        onChange(num);
      }}
      className={cn(
        "input-shell w-full rounded-2xl bg-transparent px-3.5 py-3 text-sm outline-none transition-all",
        "text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500"
      )}
    />
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder = "Todos",
}: {
  label: string;
  value?: string;
  onChange: (v: string | undefined) => void;
  options: string[];
  placeholder?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="text-[0.62rem] font-semibold uppercase tracking-[0.28em] text-slate-500 dark:text-slate-400">
        {label}
      </label>
      <SelectPrimitive.Root
        value={value ?? EMPTY_SELECT_VALUE}
        onValueChange={(nextValue) => onChange(nextValue === EMPTY_SELECT_VALUE ? undefined : nextValue)}
      >
        <SelectPrimitive.Trigger
          className={cn(
            "input-shell flex w-full items-center justify-between rounded-2xl px-3.5 py-3 text-left text-sm outline-none transition-all",
            "text-slate-900 dark:text-white"
          )}
          aria-label={label}
        >
          <SelectPrimitive.Value />
          <SelectPrimitive.Icon asChild>
            <ChevronDown className="h-4 w-4 text-slate-500" />
          </SelectPrimitive.Icon>
        </SelectPrimitive.Trigger>

        <SelectPrimitive.Portal>
          <SelectPrimitive.Content
            position="popper"
            sideOffset={8}
            className="z-50 max-h-80 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-[1.2rem] p-1.5 shadow-[0_22px_60px_rgba(1,5,14,0.42)] backdrop-blur-2xl"
            style={{
              background: "linear-gradient(180deg, rgba(255, 255, 255, 0.025), rgba(255, 255, 255, 0.01)), var(--panel-strong)",
              border: "1px solid var(--border)",
              color: "var(--text)",
            }}
          >
            <SelectPrimitive.Viewport className="max-h-80 p-0.5">
              <SelectPrimitive.Item
                value={EMPTY_SELECT_VALUE}
                className="relative flex cursor-pointer select-none items-center rounded-[0.95rem] px-3 py-2.5 pr-9 text-sm outline-none transition-colors data-[highlighted]:bg-brand-500/12"
              >
                <SelectPrimitive.ItemText>{placeholder}</SelectPrimitive.ItemText>
                <SelectPrimitive.ItemIndicator className="absolute right-3 inline-flex items-center justify-center text-brand-300">
                  <Check className="h-4 w-4" />
                </SelectPrimitive.ItemIndicator>
              </SelectPrimitive.Item>

              {options.map((opt) => (
                <SelectPrimitive.Item
                  key={opt}
                  value={opt}
                  className="relative flex cursor-pointer select-none items-center rounded-[0.95rem] px-3 py-2.5 pr-9 text-sm outline-none transition-colors data-[highlighted]:bg-brand-500/12"
                >
                  <SelectPrimitive.ItemText>{opt}</SelectPrimitive.ItemText>
                  <SelectPrimitive.ItemIndicator className="absolute right-3 inline-flex items-center justify-center text-brand-300">
                    <Check className="h-4 w-4" />
                  </SelectPrimitive.ItemIndicator>
                </SelectPrimitive.Item>
              ))}
            </SelectPrimitive.Viewport>
          </SelectPrimitive.Content>
        </SelectPrimitive.Portal>
      </SelectPrimitive.Root>
    </div>
  );
}

function RangeField({
  label,
  minValue,
  maxValue,
  onChangeMin,
  onChangeMax,
  minPlaceholder = "Mín",
  maxPlaceholder = "Máx",
}: {
  label: string;
  minValue?: number;
  maxValue?: number;
  onChangeMin: (v: number | undefined) => void;
  onChangeMax: (v: number | undefined) => void;
  min?: number;
  max?: number;
  step?: number;
  format?: (v: number) => string;
  minPlaceholder?: string;
  maxPlaceholder?: string;
}) {
  return (
    <div className="space-y-2">
      <label className="text-[0.62rem] font-semibold uppercase tracking-[0.28em] text-slate-500 dark:text-slate-400">
        {label}
      </label>
      <div className="grid grid-cols-2 gap-2">
        <NumInput value={minValue} onChange={onChangeMin} placeholder={minPlaceholder} />
        <NumInput value={maxValue} onChange={onChangeMax} placeholder={maxPlaceholder} />
      </div>
    </div>
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 pt-2">
      <span className="shrink-0 text-[0.62rem] font-semibold uppercase tracking-[0.28em] text-brand-200/70">
        {children}
      </span>
      <div className="h-px flex-1 bg-white/10" />
    </div>
  );
}

function formatQueryNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : String(value);
}

function hasAppliedSearchFilters(filters: SearchFilters): boolean {
  return Object.entries(filters).some(([key, value]) => {
    if (key === "order_by" || key === "page" || key === "per_page") {
      return false;
    }

    return value !== undefined && value !== null && value !== "";
  });
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
  const passagemLeilao = filters.passagem_leilao;
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
  if (passagemLeilao === true) {
    parts.push("com passagem por leilao");
  } else if (passagemLeilao === false) {
    parts.push("sem passagem por leilao");
  }

  return parts.join(" ");
}

// ── Campos que o FilterPanel gerencia (sem q, page, per_page, order_by) ──
type DraftFilters = Pick<SearchFilters,
  | "marca" | "modelo"
  | "ano_min" | "ano_max"
  | "km_min" | "km_max"
  | "preco_min" | "preco_max"
  | "combustivel" | "cambio" | "vendedor_tipo"
  | "estado" | "cidade"
  | "source"
  | "passagem_leilao"
>;

const DRAFT_KEYS: (keyof DraftFilters)[] = [
  "marca", "modelo", "ano_min", "ano_max", "km_min", "km_max",
  "preco_min", "preco_max", "combustivel", "cambio", "vendedor_tipo",
  "estado", "cidade", "source", "passagem_leilao",
];

function toDraft(f: SearchFilters): DraftFilters {
  return {
    marca: f.marca, modelo: f.modelo,
    ano_min: f.ano_min, ano_max: f.ano_max,
    km_min: f.km_min, km_max: f.km_max,
    preco_min: f.preco_min, preco_max: f.preco_max,
    combustivel: f.combustivel, cambio: f.cambio,
    vendedor_tipo: f.vendedor_tipo,
    estado: f.estado, cidade: f.cidade,
    source: f.source,
    passagem_leilao: f.passagem_leilao,
  };
}

export function FilterPanel() {
  const { filters, setFilters, resetFilters } = useSearchStore();
  const [expanded, setExpanded] = useState(false);
  const [showRecentSearchFeedback, setShowRecentSearchFeedback] = useState(false);
  const appliedDraft = toDraft(filters);
  const appliedDraftKey = JSON.stringify(appliedDraft);
  const appliedSmartQuery = buildSmartQuery(filters);

  // Mudanças ficam no draft até o usuário clicar "Buscar"
  const [draft, setDraft] = useState<DraftFilters>(() => toDraft(filters));
  // Último estado confirmado (para o botão Cancelar voltar)
  const [committed, setCommitted] = useState<DraftFilters>(() => toDraft(filters));

  const { data: bootstrapStatus } = useQuery({
    queryKey: ["initialBootstrapStatus"],
    queryFn: getInitialBootstrapStatus,
    refetchInterval: (query) => {
      const status = query.state.data;
      if (!status || (!status.done && status.status !== "skipped")) {
        return 1500;
      }

      return status?.running ? 1500 : false;
    },
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: false,
    staleTime: 0,
  });

  const shouldPollFilterOptions = !bootstrapStatus || (!bootstrapStatus.done && bootstrapStatus.status !== "skipped");

  const { data: options, isLoading } = useQuery({
    queryKey: ["filterOptions"],
    queryFn: getFilterOptions,
    placeholderData: (previous) => previous,
    staleTime: shouldPollFilterOptions ? 0 : 5 * 60 * 1000,
    refetchInterval: shouldPollFilterOptions ? 3000 : false,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: false,
  });

  const { data: scrapeProgress } = useQuery({
    queryKey: ["scrapeProgress", appliedSmartQuery],
    queryFn: () => getSearchScrapeProgress(appliedSmartQuery),
    enabled: appliedSmartQuery.length >= 3,
    refetchInterval: (query) => {
      const progress = query.state.data;
      if (progress?.done) {
        return false;
      }

      return progress?.running ? 1500 : false;
    },
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: false,
    staleTime: 0,
  });

  const activeVehicleRequests = useIsFetching({ queryKey: ["vehicles"] });

  const modelos = options?.modelos && draft.marca
    ? (options.modelos[draft.marca] || [])
    : [];

  const cidades = options?.cidades && draft.estado
    ? (options.cidades[draft.estado] || [])
    : [];
  const fontes = options?.fontes?.length
    ? options.fontes
    : ["OLX", "iCarros"];

  // Quantos filtros estão aplicados nos resultados agora
  const activeFiltersCount = DRAFT_KEYS.filter((k) => committed[k] !== undefined).length;

  // Há mudanças no draft que ainda não foram buscadas?
  const isDirty = DRAFT_KEYS.some((k) => draft[k] !== committed[k]);
  const isApplyingFilters = activeVehicleRequests > 0;
  const isRadarScraping = appliedSmartQuery.length >= 3 && Boolean(scrapeProgress?.running || scrapeProgress?.worker_running);
  const showFilterWarmupHint = shouldPollFilterOptions && !options?.estados?.length;
  const showSearchFeedback = showRecentSearchFeedback && !isDirty;
  const statusMessage = showFilterWarmupHint
    ? "Carregando as opções do radar conforme a base inicial é preenchida."
    : isApplyingFilters || showSearchFeedback
      ? "Aplicando filtros e atualizando os resultados agora."
      : isRadarScraping
        ? scrapeProgress?.pages_scraped
          ? `Radar consultando anúncios. ${scrapeProgress.pages_scraped} página${scrapeProgress.pages_scraped === 1 ? "" : "s"} já analisada${scrapeProgress.pages_scraped === 1 ? "" : "s"}.`
          : "Radar consultando anúncios agora."
        : null;

  useEffect(() => {
    setDraft(appliedDraft);
    setCommitted(appliedDraft);
  }, [appliedDraftKey]);

  useEffect(() => {
    if (!showRecentSearchFeedback) {
      return;
    }

    const timeout = window.setTimeout(() => {
      setShowRecentSearchFeedback(false);
    }, 4000);

    return () => window.clearTimeout(timeout);
  }, [showRecentSearchFeedback]);

  function handleSearch() {
    const snap = { ...draft };
    setCommitted(snap);
    setShowRecentSearchFeedback(true);
    setFilters(snap);
  }

  function handleCancel() {
    setDraft({ ...committed });
  }

  function handleReset() {
    const empty = toDraft({} as SearchFilters);
    setDraft(empty);
    setCommitted(empty);
    setShowRecentSearchFeedback(true);
    resetFilters();
  }

  if (isLoading) {
    return (
      <div className="surface-panel rounded-[2rem] p-4 space-y-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-10 skeleton rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="surface-panel overflow-hidden rounded-[2rem]">
      <div
        className="flex cursor-pointer items-start justify-between gap-3 p-5 lg:cursor-default"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-brand-500/15 text-brand-300">
            <SlidersHorizontal className="h-4 w-4" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-slate-900 dark:text-white">
                Refinar radar
              </span>
              {activeFiltersCount > 0 && (
                <span className="rounded-full border border-brand-400/20 bg-brand-500/15 px-2 py-0.5 text-[11px] font-bold text-brand-100">
                  {activeFiltersCount}
                </span>
              )}
              {isDirty && (
                <span
                  className="h-2 w-2 shrink-0 rounded-full bg-orange-400"
                  title="Há filtros pendentes — clique em Buscar"
                />
              )}
            </div>
            <p className="mt-1 max-w-xs text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              Ajuste faixa de preço, ano e local sem perder o contexto da busca.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {(activeFiltersCount > 0 || isDirty) && (
            <button
              onClick={(e) => { e.stopPropagation(); handleReset(); }}
              className="flex items-center gap-1 text-xs font-medium text-rose-400 transition-colors hover:text-rose-300"
            >
              <X className="w-3 h-3" />
              Limpar
            </button>
          )}
          <ChevronDown
            className={cn(
              "h-4 w-4 text-slate-500 transition-transform lg:hidden",
              expanded && "rotate-180"
            )}
          />
        </div>
      </div>

      <div className={cn("lg:block", expanded ? "block" : "hidden")}>
        <div className="scrollbar-thin space-y-4 border-t border-white/[0.06] px-5 pb-5 pt-4 lg:max-h-[calc(100vh-10.75rem)] lg:overflow-y-auto">
          <SectionHeader>Veículo</SectionHeader>

          <SelectField
            label="Marca"
            value={draft.marca}
            onChange={(v) => setDraft((d) => ({ ...d, marca: v, modelo: undefined }))}
            options={options?.marcas || []}
          />

          <SelectField
            label="Modelo"
            value={draft.modelo}
            onChange={(v) => setDraft((d) => ({ ...d, modelo: v }))}
            options={modelos}
            placeholder={draft.marca ? "Todos" : "Selecione a marca"}
          />

          <RangeField
            label="Ano"
            minValue={draft.ano_min}
            maxValue={draft.ano_max}
            onChangeMin={(v) => setDraft((d) => ({ ...d, ano_min: v }))}
            onChangeMax={(v) => setDraft((d) => ({ ...d, ano_max: v }))}
            minPlaceholder="2010"
            maxPlaceholder="2025"
          />

          <SectionHeader>Condição</SectionHeader>

          <RangeField
            label="Quilometragem (km)"
            minValue={draft.km_min}
            maxValue={draft.km_max}
            onChangeMin={(v) => setDraft((d) => ({ ...d, km_min: v }))}
            onChangeMax={(v) => setDraft((d) => ({ ...d, km_max: v }))}
            minPlaceholder="0"
            maxPlaceholder="150.000"
          />

          <SelectField
            label="Combustível"
            value={draft.combustivel}
            onChange={(v) => setDraft((d) => ({ ...d, combustivel: v }))}
            options={options?.combustiveis || ["Flex", "Gasolina", "Diesel", "Elétrico", "Híbrido"]}
          />

          <SelectField
            label="Câmbio"
            value={draft.cambio}
            onChange={(v) => setDraft((d) => ({ ...d, cambio: v }))}
            options={options?.cambios || ["Manual", "Automático", "CVT", "Automatizado"]}
          />

          <SectionHeader>Preço</SectionHeader>

          <RangeField
            label="Faixa de Preço"
            minValue={draft.preco_min}
            maxValue={draft.preco_max}
            onChangeMin={(v) => setDraft((d) => ({ ...d, preco_min: v }))}
            onChangeMax={(v) => setDraft((d) => ({ ...d, preco_max: v }))}
            minPlaceholder="R$ 20.000"
            maxPlaceholder="R$ 200.000"
          />

          <SectionHeader>Vendedor / Local</SectionHeader>

          <SelectField
            label="Tipo de Vendedor"
            value={draft.vendedor_tipo}
            onChange={(v) => setDraft((d) => ({ ...d, vendedor_tipo: v }))}
            options={options?.vendedor_tipos || ["Pessoa Física", "Loja", "Concessionária"]}
          />

          <SelectField
            label="Fonte"
            value={draft.source}
            onChange={(v) => setDraft((d) => ({ ...d, source: v }))}
            options={fontes}
          />

          <SelectField
            label="Leilão"
            value={draft.passagem_leilao === undefined ? undefined : draft.passagem_leilao ? "Sim" : "Não"}
            onChange={(v) => setDraft((d) => ({
              ...d,
              passagem_leilao: v === undefined ? undefined : v === "Sim",
            }))}
            options={["Sim", "Não"]}
            placeholder="Todos"
          />

          <SelectField
            label="Estado"
            value={draft.estado}
            onChange={(v) => setDraft((d) => ({ ...d, estado: v, cidade: undefined }))}
            options={options?.estados || []}
          />

          {draft.estado && cidades.length > 0 && (
            <SelectField
              label="Cidade"
              value={draft.cidade}
              onChange={(v) => setDraft((d) => ({ ...d, cidade: v }))}
              options={cidades}
            />
          )}

          <div className="flex gap-2 border-t border-white/[0.06] pt-2">
            <button
              onClick={handleSearch}
              className={cn(
                "flex flex-1 items-center justify-center gap-1.5 rounded-[1.2rem] py-3 text-sm font-semibold transition-all",
                isDirty || isApplyingFilters || isRadarScraping || showSearchFeedback
                  ? "primary-button"
                  : "secondary-button"
              )}
            >
              {isApplyingFilters || isRadarScraping || showSearchFeedback ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Search className="w-3.5 h-3.5" />
              )}
              {isApplyingFilters || showSearchFeedback ? "Buscando..." : isRadarScraping ? "Radar ativo" : "Buscar"}
            </button>
            {isDirty && (
              <button
                onClick={handleCancel}
                className="secondary-button rounded-[1.2rem] px-4 py-3 text-sm font-medium transition-all"
              >
                Cancelar
              </button>
            )}
          </div>

          {statusMessage && (
            <div className="flex items-start gap-2 rounded-[1.1rem] border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-xs leading-relaxed text-slate-400">
              <Loader2 className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 animate-spin text-brand-300" />
              <span>{statusMessage}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
