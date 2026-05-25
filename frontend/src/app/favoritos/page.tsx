"use client";

import { useQuery } from "@tanstack/react-query";
import { getFavorites } from "@/lib/api";
import { Header } from "@/components/ui/Header";
import { VehicleCard } from "@/components/vehicle/VehicleCard";
import { VehicleCardSkeleton } from "@/components/ui/Skeleton";
import { Heart } from "lucide-react";
import Link from "next/link";
import { useFavoriteStore } from "@/store";

export default function FavoritosPage() {
  const favoriteIds = useFavoriteStore((s) => s.favoriteIds);

  const { data: serverFavorites, isLoading } = useQuery({
    queryKey: ["favorites"],
    queryFn: getFavorites,
  });

  const vehicles = serverFavorites
    ?.filter((f) => f.vehicle)
    .map((f) => f.vehicle!) ?? [];
  const totalSaved = isLoading ? favoriteIds.length : vehicles.length;

  return (
    <div className="min-h-screen pb-16">
      <Header />
      <main className="mx-auto max-w-7xl px-4 pb-10 pt-28 sm:px-6">
        <section className="surface-panel mb-6 rounded-[2.2rem] p-6 sm:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-3">
              <span className="section-kicker">Sua shortlist</span>
              <h1 className="font-display text-4xl font-semibold tracking-[-0.04em] text-slate-900 dark:text-white sm:text-5xl">
                Favoritos prontos para decisão.
              </h1>
              <p className="max-w-2xl text-sm leading-relaxed text-slate-500 dark:text-slate-400 sm:text-base">
                Reúna os anúncios mais promissores, volte depois com calma e monte uma comparação mais séria antes de falar com o vendedor.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="surface-card rounded-[1.5rem] p-4">
                <p className="text-[0.62rem] font-semibold uppercase tracking-[0.3em] text-brand-200/70">
                  Veículos salvos
                </p>
                <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
                  {totalSaved}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                  Sua curadoria pessoal fica reunida aqui para revisão rápida.
                </p>
              </div>

              <div className="surface-card rounded-[1.5rem] p-4">
                <p className="text-[0.62rem] font-semibold uppercase tracking-[0.3em] text-brand-200/70">
                  Próximo passo
                </p>
                <p className="mt-3 text-sm font-semibold text-slate-900 dark:text-white">
                  Abra as fichas e compare score, localização, FIPE e sinais de confiança.
                </p>
              </div>
            </div>
          </div>
        </section>

        {isLoading ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {[...Array(3)].map((_, i) => <VehicleCardSkeleton key={i} />)}
          </div>
        ) : vehicles.length === 0 ? (
          <div className="surface-panel flex flex-col items-center justify-center rounded-[2rem] px-6 py-16 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-[1.6rem] bg-brand-500/10">
              <Heart className="h-8 w-8 text-brand-300" />
            </div>
            <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
              Nenhum favorito ainda
            </h2>
            <p className="mb-6 max-w-md text-sm text-slate-500 dark:text-slate-400">
              Salve os veículos que mais interessam para acessar rapidamente.
            </p>
            <Link
              href="/"
              className="primary-button rounded-[1.3rem] px-6 py-3 text-sm font-semibold transition-all"
            >
              Explorar veículos
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {vehicles.map((vehicle) => (
              <VehicleCard key={vehicle.id} vehicle={vehicle} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
