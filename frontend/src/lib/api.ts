import axios from "axios";
import type {
  SearchFilters,
  SearchResponse,
  Vehicle,
  FilterOptions,
  FavoriteItem,
  InitialBootstrapStatus,
  ScraperStatus,
  ScrapeProgress,
} from "@/types";

const LOCALHOST_NAMES = new Set(["localhost", "127.0.0.1", "::1"]);

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function isLocalHostname(hostname: string): boolean {
  return LOCALHOST_NAMES.has(hostname);
}

function resolveApiBase(): string {
  const configuredBase = process.env.NEXT_PUBLIC_API_URL?.trim();

  if (typeof window === "undefined") {
    return trimTrailingSlash(configuredBase || "http://localhost:8000/api");
  }

  if (!configuredBase) {
    return `${window.location.protocol}//${window.location.hostname}:8000/api`;
  }

  try {
    const configuredUrl = new URL(configuredBase);

    if (!isLocalHostname(window.location.hostname) && isLocalHostname(configuredUrl.hostname)) {
      configuredUrl.protocol = window.location.protocol;
      configuredUrl.hostname = window.location.hostname;
    }

    return trimTrailingSlash(configuredUrl.toString());
  } catch {
    return trimTrailingSlash(configuredBase);
  }
}

const API_BASE = resolveApiBase();

/**
 * Domains whose images need to be proxied through the backend to bypass
 * hotlink-protection (Referer checks on their CDNs).
 */
const PROXY_DOMAINS = [
  "olx.com.br",
  "olxcdn.com",
  "akamaized.net",
  "webmotors.com.br",
  "icarros.com.br",
  "icarros.com",
  "napista.com.br",
  "cloudfront.net",
  "mlstatic.com",
  "mlcdn.com.br",
];

export function proxyImg(url: string | undefined | null): string {
  if (!url) return "";
  try {
    const { hostname } = new URL(url);
    if (PROXY_DOMAINS.some((d) => hostname === d || hostname.endsWith("." + d))) {
      return `${API_BASE}/images/proxy?url=${encodeURIComponent(url)}`;
    }
  } catch {
    // not a valid URL — return as-is
  }
  return url;
}

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const sessionId = getOrCreateSessionId();
    config.headers["x-session-id"] = sessionId;
  }
  return config;
});

function getOrCreateSessionId(): string {
  let sessionId = localStorage.getItem("deepcar_session");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem("deepcar_session", sessionId);
  }
  return sessionId;
}

export async function searchVehicles(
  filters: SearchFilters
): Promise<SearchResponse> {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([k, v]) => {
      if (v === undefined || v === "" || v === null) return false;
      if ((k === "ano_min" || k === "ano_max") && Number(v) < 1950) return false;
      return true;
    })
  );
  const { data } = await api.get("/search", { params });
  return data;
}

export async function getVehicle(id: number): Promise<Vehicle> {
  const { data } = await api.get(`/car/${id}`);
  return data;
}

export async function getFilterOptions(): Promise<FilterOptions> {
  const { data } = await api.get("/filters");
  return data;
}

export async function getFavorites(): Promise<FavoriteItem[]> {
  const { data } = await api.get("/favorites");
  return data;
}

export async function addFavorite(vehicleId: number): Promise<void> {
  await api.post(`/favorites/${vehicleId}`);
}

export async function removeFavorite(vehicleId: number): Promise<void> {
  await api.delete(`/favorites/${vehicleId}`);
}

export async function getScraperStatus(): Promise<ScraperStatus[]> {
  const { data } = await api.get("/scraper/status");
  return data;
}

export async function getInitialBootstrapStatus(): Promise<InitialBootstrapStatus> {
  const { data } = await api.get("/scraper/bootstrap-status");
  return data;
}

export async function runScraper(source: string): Promise<void> {
  await api.post(`/scraper/run/${source}`);
}

export async function cancelQueryScrape(q: string): Promise<{
  query: string;
  task_cancelled: boolean;
  worker_cancelled: boolean;
}> {
  const { data } = await api.post(`/scraper/cancel?q=${encodeURIComponent(q)}`);
  return data;
}

export async function getSearchScrapeProgress(q: string): Promise<ScrapeProgress> {
  const { data } = await api.get(`/scraper/progress?q=${encodeURIComponent(q)}`);
  return data;
}

export async function triggerLiveScrape(q: string): Promise<{ eta_seconds: number }> {
  const { data } = await api.post(`/scraper/live?q=${encodeURIComponent(q)}`);
  return data;
}

export function openLiveScrapeStream(
  q: string,
  onProgress: (data: { source: string; saved: number }) => void,
  onDone: (total: number) => void
): () => void {
  const url = `${API_BASE}/scraper/live/stream?q=${encodeURIComponent(q)}`;
  const es = new EventSource(url);

  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.done) {
        onDone(data.total ?? 0);
        es.close();
      } else {
        onProgress(data);
      }
    } catch {
      // ignore malformed events
    }
  };

  es.onerror = () => {
    es.close();
    onDone(0);
  };

  return () => es.close();
}

export { getOrCreateSessionId };
