import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { searchVehicles, getVehicle, getFilterOptions, getFavorites, addFavorite, removeFavorite } from "@/lib/api";
import type { SearchFilters } from "@/types";

export function useVehicleSearch(filters: SearchFilters) {
  return useQuery({
    queryKey: ["vehicles", filters],
    queryFn: () => searchVehicles(filters),
    placeholderData: (prev) => prev,
  });
}

export function useVehicle(id: number) {
  return useQuery({
    queryKey: ["vehicle", id],
    queryFn: () => getVehicle(id),
    enabled: !!id,
  });
}

export function useFilterOptions() {
  return useQuery({
    queryKey: ["filterOptions"],
    queryFn: getFilterOptions,
    staleTime: 5 * 60 * 1000,
  });
}

export function useFavorites() {
  return useQuery({
    queryKey: ["favorites"],
    queryFn: getFavorites,
  });
}

export function useToggleFavorite() {
  const queryClient = useQueryClient();

  const add = useMutation({
    mutationFn: (id: number) => addFavorite(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["favorites"] }),
  });

  const remove = useMutation({
    mutationFn: (id: number) => removeFavorite(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["favorites"] }),
  });

  return { add, remove };
}
