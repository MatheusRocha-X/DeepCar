import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { SearchFilters, OrderBy } from "@/types";

interface SearchState {
  filters: SearchFilters;
  hasHydrated: boolean;
  setFilters: (filters: Partial<SearchFilters>) => void;
  resetFilters: () => void;
  setPage: (page: number) => void;
  setOrderBy: (order: OrderBy) => void;
  setHasHydrated: (hasHydrated: boolean) => void;
}

const defaultFilters: SearchFilters = {
  page: 1,
  per_page: 20,
  order_by: "score",
};

export const useSearchStore = create<SearchState>()(
  persist(
    (set) => ({
      filters: defaultFilters,
      hasHydrated: false,
      setFilters: (newFilters) =>
        set((state) => ({
          filters: { ...state.filters, ...newFilters, page: 1 },
        })),
      resetFilters: () => set({ filters: defaultFilters }),
      setPage: (page) =>
        set((state) => ({ filters: { ...state.filters, page } })),
      setOrderBy: (order_by) =>
        set((state) => ({ filters: { ...state.filters, order_by, page: 1 } })),
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
    }),
    {
      name: "deepcar-search",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({ filters: state.filters }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

interface FavoriteStore {
  favoriteIds: number[];
  addFavorite: (id: number) => void;
  removeFavorite: (id: number) => void;
  isFavorite: (id: number) => boolean;
}

export const useFavoriteStore = create<FavoriteStore>()(
  persist(
    (set, get) => ({
      favoriteIds: [],
      addFavorite: (id) =>
        set((state) => ({
          favoriteIds: state.favoriteIds.includes(id)
            ? state.favoriteIds
            : [...state.favoriteIds, id],
        })),
      removeFavorite: (id) =>
        set((state) => ({
          favoriteIds: state.favoriteIds.filter((fId) => fId !== id),
        })),
      isFavorite: (id) => get().favoriteIds.includes(id),
    }),
    { name: "deepcar-favorites" }
  )
);
