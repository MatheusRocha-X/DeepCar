"use client";

import Image from "next/image";
import Link from "next/link";
import { Heart, MapPin, Gauge, Calendar, Fuel, Settings, ArrowRight } from "lucide-react";
import { cn, formatPrice, formatKm, getScoreLabel, getVehicleImageFallback } from "@/lib/utils";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { InsightBadge } from "@/components/ui/InsightBadge";
import type { Vehicle } from "@/types";
import { useFavoriteStore } from "@/store";
import { addFavorite, removeFavorite, proxyImg } from "@/lib/api";
import { useState } from "react";

interface VehicleCardProps {
  vehicle: Vehicle;
  index?: number;
}

export function VehicleCard({ vehicle, index = 0 }: VehicleCardProps) {
  const { isFavorite, addFavorite: addLocal, removeFavorite: removeLocal } = useFavoriteStore();
  const favorited = isFavorite(vehicle.id);
  const [loading, setLoading] = useState(false);
  const [imgError, setImgError] = useState(false);

  const mainImage = !imgError && vehicle.fotos?.[0]
    ? proxyImg(vehicle.fotos[0])
    : getVehicleImageFallback();

  async function toggleFavorite(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (loading) return;
    setLoading(true);
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
      setLoading(false);
    }
  }

  return (
    <Link
      href={`/veiculo/${vehicle.id}`}
      className="group block animate-fade-in-up"
      style={{ animationDelay: `${Math.min(index * 40, 400)}ms` }}
    >
      <article className="surface-card surface-card-hover overflow-hidden rounded-[1.9rem]">
        <div className="relative h-60 overflow-hidden bg-[#050505]">
          <Image
            src={mainImage}
            alt={vehicle.titulo}
            fill
            unoptimized
            className="object-cover transition-transform duration-500 ease-out group-hover:scale-[1.04]"
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
            onError={() => setImgError(true)}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#090909] via-[#090909]/48 to-transparent" />

          <div className="absolute inset-x-4 top-4 flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="rounded-[1.2rem] border border-white/[0.06] bg-[#111111]/68 p-2.5 backdrop-blur-xl">
                <ScoreRing score={vehicle.score} size="sm" />
              </div>
            </div>

            <button
              onClick={toggleFavorite}
              disabled={loading}
              className={cn(
                "flex h-9 w-9 items-center justify-center rounded-full border border-white/[0.06] bg-[#111111]/68 text-white/80 backdrop-blur-xl transition-all duration-200",
                favorited ? "text-rose-300" : "hover:text-rose-300"
              )}
              aria-label={favorited ? "Remover dos favoritos" : "Adicionar aos favoritos"}
            >
              <Heart className={cn("h-3.5 w-3.5", favorited && "fill-current")} />
            </button>
          </div>

          <div className="absolute inset-x-4 bottom-4">
            {(vehicle.cidade || vehicle.estado) && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-[#111111]/66 px-3 py-1 text-xs text-white/80 backdrop-blur-xl">
                <MapPin className="h-3.5 w-3.5 text-brand-300" />
                {[vehicle.cidade, vehicle.estado].filter(Boolean).join(", ")}
              </span>
            )}
            <h3 className="mt-3 font-display text-[1.32rem] font-semibold leading-tight text-white line-clamp-2">
              {vehicle.titulo}
            </h3>
          </div>
        </div>

        <div className="space-y-4 p-5">
          <div className="flex items-end justify-between gap-3">
            <div>
              <p className="text-[0.62rem] font-semibold uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">
                Preço anunciado
              </p>
              <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
                {formatPrice(vehicle.preco)}
              </p>
            </div>
            <div className="rounded-[1.3rem] border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-right">
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Leitura
              </p>
              <p className="mt-1 text-sm font-semibold text-brand-300">
                {getScoreLabel(vehicle.score)}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {vehicle.km !== undefined && (
              <span className="data-chip text-xs font-medium">
                <Gauge className="h-3.5 w-3.5 text-brand-300" />
                {formatKm(vehicle.km)}
              </span>
            )}
            {vehicle.ano && (
              <span className="data-chip text-xs font-medium">
                <Calendar className="h-3.5 w-3.5 text-brand-300" />
                {vehicle.ano}
              </span>
            )}
            {vehicle.combustivel && (
              <span className="data-chip text-xs font-medium">
                <Fuel className="h-3.5 w-3.5 text-brand-300" />
                {vehicle.combustivel}
              </span>
            )}
            {vehicle.cambio && (
              <span className="data-chip text-xs font-medium">
                <Settings className="h-3.5 w-3.5 text-brand-300" />
                {vehicle.cambio}
              </span>
            )}
          </div>

          {vehicle.insights && vehicle.insights.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {vehicle.insights.slice(0, 2).map((insight, i) => (
                <InsightBadge key={i} insight={insight} />
              ))}
              {vehicle.insights.length > 2 && (
                <span className="inline-flex items-center rounded-full border border-white/[0.06] bg-white/[0.03] px-3 py-1 text-xs font-semibold text-slate-400">
                  +{vehicle.insights.length - 2}
                </span>
              )}
            </div>
          )}

          <div className="flex items-center justify-between border-t border-white/[0.06] pt-3.5">
            <span className="truncate text-sm text-slate-500 dark:text-slate-400">
              {vehicle.vendedor_tipo || "Particular"}
            </span>
            <span className="flex items-center gap-2 text-sm font-semibold text-brand-300">
              Abrir ficha
              <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
            </span>
          </div>
        </div>
      </article>
    </Link>
  );
}
