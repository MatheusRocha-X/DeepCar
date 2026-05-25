export interface Vehicle {
  id: number;
  titulo: string;
  marca: string;
  modelo: string;
  versao?: string;
  ano?: number;
  km?: number;
  preco?: number;
  cambio?: string;
  combustivel?: string;
  cidade?: string;
  estado?: string;
  vendedor_tipo?: string;
  descricao?: string;
  fotos: string[];
  source_url: string;
  source_name: string;
  score: number;
  insights: string[];
  fipe_preco?: number;
  ativo?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface SearchResponse {
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  results: Vehicle[];
}

export interface FilterOptions {
  marcas: string[];
  modelos: Record<string, string[]>;
  estados: string[];
  cidades: Record<string, string[]>;
  combustiveis: string[];
  cambios: string[];
  vendedor_tipos: string[];
  fontes: string[];
  preco_min?: number;
  preco_max?: number;
  ano_min?: number;
  ano_max?: number;
}

export interface SearchFilters {
  q?: string;
  marca?: string;
  modelo?: string;
  ano_min?: number;
  ano_max?: number;
  km_min?: number;
  km_max?: number;
  preco_min?: number;
  preco_max?: number;
  vendedor_tipo?: string;
  combustivel?: string;
  cambio?: string;
  estado?: string;
  cidade?: string;
  source?: string;
  order_by?: OrderBy;
  page?: number;
  per_page?: number;
}

export type OrderBy =
  | "score"
  | "menor_preco"
  | "maior_preco"
  | "menor_km"
  | "mais_recente";

export interface FavoriteItem {
  id: number;
  session_id: string;
  vehicle_id: number;
  vehicle?: Vehicle;
  created_at?: string;
}

export interface ScraperStatus {
  source: string;
  status: string;
  last_run?: string;
  total_collected: number;
  errors: number;
}

export interface ScrapeProgress {
  query: string;
  status: string;
  running: boolean;
  done: boolean;
  pages_scraped: number;
  saved_total: number;
  display_ready: boolean;
  min_pages_before_display: number;
  task_running: boolean;
  worker_running: boolean;
  started_at?: string | null;
  updated_at?: string | null;
}

export interface InitialBootstrapStatus {
  status: string;
  running: boolean;
  done: boolean;
  triggered: boolean;
  needs_initial_load: boolean;
  message: string;
  current_source?: string | null;
  targets: Record<string, number>;
  saved_by_source: Record<string, number>;
  remaining_by_source: Record<string, number>;
  total_target: number;
  total_saved: number;
  started_at?: string | null;
  updated_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
}
