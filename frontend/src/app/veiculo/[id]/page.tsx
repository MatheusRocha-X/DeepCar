"use client";

import { use, useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getVehicle, addFavorite, removeFavorite, proxyImg } from "@/lib/api";
import { Header } from "@/components/ui/Header";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { InsightBadge } from "@/components/ui/InsightBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  formatPrice,
  formatKm,
  formatDate,
  getScoreLabel,
  getScoreColor,
  cn,
} from "@/lib/utils";
import {
  MapPin,
  Gauge,
  Calendar,
  Fuel,
  Settings,
  Heart,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  User,
  Building2,
  Store,
  Maximize2,
  X as XIcon,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useFavoriteStore } from "@/store";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function VehiclePage({ params }: PageProps) {
  const { id } = use(params);
  const vehicleId = parseInt(id);

  const { data: vehicle, isLoading, isError } = useQuery({
    queryKey: ["vehicle", vehicleId],
    queryFn: () => getVehicle(vehicleId),
    enabled: !!vehicleId,
  });

  const { isFavorite, addFavorite: addLocal, removeFavorite: removeLocal } = useFavoriteStore();
  const favorited = vehicle ? isFavorite(vehicle.id) : false;
  const [favLoading, setFavLoading] = useState(false);
  const [activePhoto, setActivePhoto] = useState(0);
  const [lightbox, setLightbox] = useState(false);

  const photos: string[] = (vehicle?.fotos ?? []).map(proxyImg);

  function prevPhoto() {
    if (!photos.length) return;
    setActivePhoto((p) => (p - 1 + photos.length) % photos.length);
  }
  function nextPhoto() {
    if (!photos.length) return;
    setActivePhoto((p) => (p + 1) % photos.length);
  }

  // Keyboard navigation
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowLeft") prevPhoto();
      else if (e.key === "ArrowRight") nextPhoto();
      else if (e.key === "Escape") setLightbox(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [photos.length]);

  async function toggleFavorite() {
    if (!vehicle || favLoading) return;
    setFavLoading(true);
    try {
      if (favorited) {
        await removeFavorite(vehicle.id);
        removeLocal(vehicle.id);
      } else {
        await addFavorite(vehicle.id);
        addLocal(vehicle.id);
      }
    } catch {
      if (!favorited) addLocal(vehicle.id);
      else removeLocal(vehicle.id);
    } finally {
      setFavLoading(false);
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen pb-16">
        <Header />
        <div className="mx-auto max-w-6xl space-y-6 px-4 pb-12 pt-28 sm:px-6">
          <Skeleton className="h-10 w-56" />
          <Skeleton className="h-[24rem] w-full rounded-[2rem]" />
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.2fr)_360px]">
            <div className="space-y-4">
              <Skeleton className="h-10 w-3/4" />
              <Skeleton className="h-8 w-1/3" />
              <Skeleton className="h-40 w-full rounded-[2rem]" />
            </div>
            <Skeleton className="h-72 rounded-[2rem]" />
          </div>
        </div>
      </div>
    );
  }

  if (isError || !vehicle) {
    return (
      <div className="min-h-screen pb-16">
        <Header />
        <div className="mx-auto max-w-4xl px-4 pb-12 pt-28 sm:px-6">
          <div className="surface-panel rounded-[2rem] px-6 py-16 text-center">
            <h1 className="font-display text-3xl font-semibold tracking-[-0.03em] text-slate-900 dark:text-white">
              Veículo não encontrado
            </h1>
            <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
              Esse anúncio pode ter saído do ar ou o identificador informado não existe mais.
            </p>
            <Link href="/" className="primary-button mt-6 inline-flex rounded-[1.3rem] px-5 py-3 text-sm font-semibold transition-all">
              Voltar à busca
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const vendedorMap: Record<string, React.ReactNode> = {
    "Concessionária": <Building2 className="w-4 h-4" />,
    "Loja": <Store className="w-4 h-4" />,
    "Pessoa Física": <User className="w-4 h-4" />,
  };

  const specs = [
    { label: "Ano", value: vehicle.ano, icon: <Calendar className="w-4 h-4" /> },
    { label: "KM", value: formatKm(vehicle.km), icon: <Gauge className="w-4 h-4" /> },
    { label: "Combustível", value: vehicle.combustivel, icon: <Fuel className="w-4 h-4" /> },
    { label: "Câmbio", value: vehicle.cambio, icon: <Settings className="w-4 h-4" /> },
  ].filter((s) => s.value);

  const locationLabel = [vehicle.cidade, vehicle.estado].filter(Boolean).join(", ");
  const publishedLabel = vehicle.created_at ? formatDate(vehicle.created_at) : undefined;
  const fipeDelta = vehicle.preco && vehicle.fipe_preco
    ? Math.round((Math.abs(vehicle.fipe_preco - vehicle.preco) / vehicle.fipe_preco) * 100)
    : undefined;
  const isBelowFipe = vehicle.preco !== undefined && vehicle.fipe_preco !== undefined
    ? vehicle.preco <= vehicle.fipe_preco
    : undefined;

  return (
    <div className="min-h-screen pb-16">
      <Header />

      <main className="mx-auto max-w-6xl px-4 pb-12 pt-28 sm:px-6">
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <Link
            href="/"
            className="secondary-button inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-all"
          >
            <ChevronLeft className="h-4 w-4" />
            Voltar aos resultados
          </Link>

          <span className="data-chip text-xs font-semibold uppercase tracking-[0.22em]">
            {vehicle.source_name}
          </span>

          {publishedLabel && (
            <span className="data-chip text-xs font-medium">
              Publicado em {publishedLabel}
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.2fr)_360px]">
          <div className="space-y-6">
            {photos.length > 0 ? (
              <div className="surface-panel rounded-[2.2rem] p-4 sm:p-5">
                <div className="group relative h-[20rem] w-full overflow-hidden rounded-[1.8rem] bg-[#050505] sm:h-[30rem]">
                  <Image
                    src={photos[activePhoto]}
                    alt={`${vehicle.titulo} - foto ${activePhoto + 1}`}
                    fill
                    className="cursor-zoom-in object-cover transition-transform duration-500 ease-out group-hover:scale-[1.02]"
                    sizes="(max-width: 1024px) 100vw, 66vw"
                    priority
                    unoptimized
                    onClick={() => setLightbox(true)}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#090909] via-[#090909]/42 to-transparent" />

                  <div className="absolute left-4 top-4 flex flex-wrap gap-2">
                    <span className="rounded-full border border-white/[0.06] bg-[#111111]/66 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-brand-200 backdrop-blur-xl">
                      {vehicle.source_name}
                    </span>
                    {locationLabel && (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-[#111111]/66 px-3 py-1 text-xs text-white/80 backdrop-blur-xl">
                        <MapPin className="h-3.5 w-3.5 text-brand-300" />
                        {locationLabel}
                      </span>
                    )}
                  </div>

                  <div className="absolute bottom-4 right-4 rounded-full border border-white/[0.06] bg-[#111111]/66 px-3 py-1 text-xs font-medium text-white/75 backdrop-blur-xl">
                    {activePhoto + 1} / {photos.length}
                  </div>

                  <button
                    onClick={() => setLightbox(true)}
                    className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full border border-white/[0.06] bg-[#111111]/66 text-white/80 opacity-0 backdrop-blur-xl transition-all group-hover:opacity-100 hover:text-white"
                    aria-label="Abrir galeria em tela cheia"
                  >
                    <Maximize2 className="h-4 w-4" />
                  </button>

                  {photos.length > 1 && (
                    <>
                      <button
                        onClick={prevPhoto}
                        className="absolute left-4 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-white/[0.06] bg-[#111111]/66 text-white/80 opacity-0 backdrop-blur-xl transition-all group-hover:opacity-100 hover:text-white"
                        aria-label="Foto anterior"
                      >
                        <ChevronLeft className="h-5 w-5" />
                      </button>
                      <button
                        onClick={nextPhoto}
                        className="absolute right-4 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-white/[0.06] bg-[#111111]/66 text-white/80 opacity-0 backdrop-blur-xl transition-all group-hover:opacity-100 hover:text-white"
                        aria-label="Próxima foto"
                      >
                        <ChevronRight className="h-5 w-5" />
                      </button>
                    </>
                  )}
                </div>

                {photos.length > 1 && (
                  <div className="mt-4 flex gap-2 overflow-x-auto scrollbar-hide pb-1">
                    {photos.map((photo, i) => (
                      <button
                        key={i}
                        onClick={() => setActivePhoto(i)}
                        className={cn(
                          "relative h-16 w-16 flex-shrink-0 overflow-hidden rounded-[1rem] border transition-all",
                          activePhoto === i
                            ? "border-brand-400 shadow-[0_0_0_3px_rgba(199,160,102,0.2)] opacity-100"
                            : "border-white/[0.06] opacity-60 hover:opacity-100"
                        )}
                      >
                        <Image
                          src={photo}
                          alt={`Foto ${i + 1}`}
                          fill
                          className="object-cover"
                          sizes="64px"
                          unoptimized
                        />
                      </button>
                    ))}
                  </div>
                )}

                {lightbox && (
                  <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
                    onClick={() => setLightbox(false)}
                  >
                    <button
                      className="absolute right-4 top-4 flex h-11 w-11 items-center justify-center rounded-full border border-white/[0.06] bg-white/[0.08] text-white transition-colors hover:bg-white/[0.12]"
                      onClick={() => setLightbox(false)}
                    >
                      <XIcon className="h-6 w-6" />
                    </button>
                    {photos.length > 1 && (
                      <>
                        <button
                          className="absolute left-4 top-1/2 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20"
                          onClick={(e) => { e.stopPropagation(); prevPhoto(); }}
                        >
                          <ChevronLeft className="h-6 w-6" />
                        </button>
                        <button
                          className="absolute right-4 top-1/2 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20"
                          onClick={(e) => { e.stopPropagation(); nextPhoto(); }}
                        >
                          <ChevronRight className="h-6 w-6" />
                        </button>
                      </>
                    )}
                    <div className="relative mx-8 max-h-[80vh] w-full max-w-4xl" onClick={(e) => e.stopPropagation()}>
                      <img
                        src={photos[activePhoto]}
                        alt={`${vehicle.titulo} - foto ${activePhoto + 1}`}
                        className="w-full h-full object-contain max-h-[80vh]"
                      />
                    </div>
                    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/70 text-sm">
                      {activePhoto + 1} / {photos.length}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="surface-panel flex h-72 items-center justify-center rounded-[2.2rem] px-6">
                <span className="text-slate-500">Sem fotos disponíveis</span>
              </div>
            )}

            <section className="surface-panel rounded-[2.2rem] p-6 sm:p-8">
              <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                <div className="max-w-3xl space-y-3">
                  <span className="section-kicker">Ficha do anúncio</span>
                  <h1 className="font-display text-3xl font-semibold leading-tight tracking-[-0.04em] text-slate-900 dark:text-white sm:text-5xl">
                    {vehicle.titulo}
                  </h1>
                  {vehicle.versao && (
                    <p className="text-sm leading-relaxed text-slate-500 dark:text-slate-400 sm:text-base">
                      {vehicle.versao}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {vehicle.vendedor_tipo && (
                      <span className="data-chip text-xs font-medium">{vehicle.vendedor_tipo}</span>
                    )}
                    {locationLabel && (
                      <span className="data-chip text-xs font-medium">{locationLabel}</span>
                    )}
                  </div>
                </div>

                <div className="rounded-[1.6rem] border border-white/[0.06] bg-white/[0.03] px-5 py-4">
                  <p className="text-[0.62rem] font-semibold uppercase tracking-[0.3em] text-brand-200/70">
                    Preço anunciado
                  </p>
                  <p className="mt-2 text-4xl font-semibold tracking-tight text-brand-300">
                    {formatPrice(vehicle.preco)}
                  </p>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-2 gap-3 xl:grid-cols-4">
                {specs.map((spec) => (
                  <div
                    key={spec.label}
                    className="rounded-[1.5rem] border border-white/[0.06] bg-white/[0.03] p-4"
                  >
                    <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-500/15 text-brand-300">
                      {spec.icon}
                    </span>
                    <span className="mt-4 block text-[0.62rem] font-semibold uppercase tracking-[0.28em] text-slate-500 dark:text-slate-400">
                      {spec.label}
                    </span>
                    <span className="mt-1 block text-sm font-semibold text-slate-900 dark:text-white">
                      {spec.value}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {vehicle.descricao && (
              <section className="surface-panel rounded-[2.2rem] p-6 sm:p-8">
                <h2 className="font-display text-2xl font-semibold tracking-[-0.03em] text-slate-900 dark:text-white">
                  Descrição
                </h2>
                <p className="mt-4 whitespace-pre-line text-sm leading-relaxed text-slate-600 dark:text-slate-300 sm:text-base">
                  {vehicle.descricao}
                </p>
              </section>
            )}
          </div>

          <aside className="self-start space-y-4 xl:sticky xl:top-28">
            <section className="surface-panel rounded-[2rem] p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[0.62rem] font-semibold uppercase tracking-[0.3em] text-brand-200/70">
                    Radar DeepCar
                  </p>
                  <p className={cn("mt-2 text-lg font-semibold", getScoreColor(vehicle.score))}>
                    {getScoreLabel(vehicle.score)}
                  </p>
                </div>
                <ScoreRing score={vehicle.score} size="lg" showLabel={false} />
              </div>

              {vehicle.insights && vehicle.insights.length > 0 && (
                <div className="mt-5 space-y-2">
                  <p className="text-[0.62rem] font-semibold uppercase tracking-[0.28em] text-slate-500 dark:text-slate-400">
                    Insights
                  </p>
                  {vehicle.insights.map((insight, i) => (
                    <InsightBadge key={i} insight={insight} className="w-full justify-start" />
                  ))}
                </div>
              )}

              {vehicle.fipe_preco && (
                <div className="mt-5 rounded-[1.6rem] border border-white/[0.06] bg-white/[0.03] p-4">
                  <p className="text-[0.62rem] font-semibold uppercase tracking-[0.28em] text-slate-500 dark:text-slate-400">
                      Tabela FIPE
                  </p>
                  <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">
                    {formatPrice(vehicle.fipe_preco)}
                  </p>
                  {fipeDelta !== undefined && isBelowFipe !== undefined && (
                    <p className={cn(
                      "mt-2 text-sm font-semibold",
                      isBelowFipe ? "text-emerald-300" : "text-rose-300"
                    )}>
                      {isBelowFipe ? `${fipeDelta}% abaixo da FIPE` : `${fipeDelta}% acima da FIPE`}
                    </p>
                  )}
                </div>
              )}

              <div className="mt-5 space-y-3 border-t border-white/[0.06] pt-4 text-sm text-slate-300">
                {locationLabel && (
                  <div className="flex items-center gap-3">
                    <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-brand-500/12 text-brand-300">
                      <MapPin className="h-4 w-4" />
                    </span>
                    <span>{locationLabel}</span>
                  </div>
                )}
                {vehicle.vendedor_tipo && (
                  <div className="flex items-center gap-3">
                    <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-brand-500/12 text-brand-300">
                      {vendedorMap[vehicle.vendedor_tipo] || <User className="h-4 w-4" />}
                    </span>
                    <span>{vehicle.vendedor_tipo}</span>
                  </div>
                )}
                <div className="flex items-center gap-3">
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-brand-500/12 text-brand-300 text-[10px] font-bold uppercase tracking-[0.22em]">
                    {vehicle.source_name.slice(0, 3)}
                  </span>
                  <span>Fonte: {vehicle.source_name}</span>
                </div>
                {publishedLabel && (
                  <div className="flex items-center gap-3 text-slate-400">
                    <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/5 text-slate-300">
                      <Calendar className="h-4 w-4" />
                    </span>
                    <span>Publicado em {publishedLabel}</span>
                  </div>
                )}
              </div>

              <div className="mt-5 space-y-2">
                <a
                  href={vehicle.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="primary-button flex w-full items-center justify-center gap-2 rounded-[1.3rem] px-4 py-3 text-sm font-semibold transition-all"
                >
                  Ver anúncio original
                  <ExternalLink className="h-4 w-4" />
                </a>
                <button
                  onClick={toggleFavorite}
                  disabled={favLoading}
                  className={cn(
                    "flex w-full items-center justify-center gap-2 rounded-[1.3rem] px-4 py-3 text-sm font-semibold transition-all",
                    favorited
                      ? "border border-rose-400/25 bg-rose-500/10 text-rose-200"
                      : "secondary-button text-slate-300 hover:text-white"
                  )}
                >
                  <Heart className={cn("h-4 w-4", favorited && "fill-current text-rose-300")} />
                  {favorited ? "Remover dos favoritos" : "Adicionar aos favoritos"}
                </button>
              </div>
            </section>
          </aside>
        </div>
      </main>
    </div>
  );
}
