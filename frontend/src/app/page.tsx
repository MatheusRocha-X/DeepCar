"use client";

import { Header } from "@/components/ui/Header";
import { SearchBar } from "@/components/search/SearchBar";
import { FilterPanel } from "@/components/search/FilterPanel";
import { VehicleGrid } from "@/components/vehicle/VehicleGrid";

export default function Home() {
  return (
    <div className="min-h-screen pb-16">
      <Header />

      <main className="mx-auto flex max-w-7xl flex-col gap-10 px-4 pb-10 pt-28 sm:px-6 lg:pt-32">
        <section className="pb-1">
          <div className="max-w-4xl space-y-5">
            <span className="section-kicker animate-fade-in-up">Decisão de compra com radar</span>

            <div className="max-w-3xl animate-fade-in-up" style={{ animationDelay: "160ms" }}>
              <SearchBar />
            </div>

            <p
              className="max-w-2xl text-sm leading-relaxed text-slate-500 dark:text-slate-400 animate-fade-in"
              style={{ animationDelay: "240ms" }}
            >
              Digite marca, modelo, versão ou contexto da sua busca e deixe os filtros trabalharem só quando você precisar deles.
            </p>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)] xl:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="w-full lg:w-auto lg:flex-shrink-0">
            <div className="lg:sticky lg:top-28 lg:max-h-[calc(100vh-8.5rem)]">
              <FilterPanel />
            </div>
          </aside>

          <div className="min-w-0 space-y-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <span className="section-kicker">Seleção em tempo real</span>
                <h2 className="font-display mt-3 text-2xl font-semibold text-slate-950 dark:text-white sm:text-3xl">
                  Resultados organizados para leitura rápida.
                </h2>
              </div>
              <p className="max-w-md text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                Use os filtros só quando precisar e navegue por anúncios com menos distração visual.
              </p>
            </div>

            <VehicleGrid />
          </div>
        </section>
      </main>
    </div>
  );
}
