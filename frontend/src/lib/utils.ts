import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Formata número inteiro com separador de milhar pt-BR (ex: 150000 → "150.000"). */
function ptBRInt(value: number): string {
  return Math.round(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export function formatPrice(value?: number): string {
  if (value === undefined || value === null) return "Consultar";
  return `R$\u00a0${ptBRInt(value)}`;
}

export function formatKm(value?: number): string {
  if (value === undefined || value === null) return "—";
  if (value === 0) return "0 km";
  return `${ptBRInt(value)} km`;
}

export function formatDate(dateStr?: string): string {
  if (!dateStr) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(dateStr));
}

export function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-emerald-400";
  if (score >= 40) return "text-yellow-500";
  if (score >= 20) return "text-orange-500";
  return "text-red-500";
}

export function getScoreBg(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-emerald-400";
  if (score >= 40) return "bg-yellow-500";
  if (score >= 20) return "bg-orange-500";
  return "bg-red-500";
}

export function getScoreLabel(score: number): string {
  if (score >= 80) return "Excelente";
  if (score >= 60) return "Bom";
  if (score >= 40) return "Regular";
  if (score >= 20) return "Ruim";
  return "Muito Ruim";
}

export function getInsightColor(insight: string): string {
  const lower = insight.toLowerCase();
  if (
    lower.includes("abaixo") ||
    lower.includes("baixa") ||
    lower.includes("excelente") ||
    lower.includes("bom custo") ||
    lower.includes("zero km") ||
    lower.includes("muitas fotos")
  ) {
    return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
  }
  if (
    lower.includes("suspeito") ||
    lower.includes("elevada") ||
    lower.includes("acima") ||
    lower.includes("revisar") ||
    lower.includes("sem foto") ||
    lower.includes("poucas foto") ||
    lower.includes("duplicado") ||
    lower.includes("spam")
  ) {
    return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
  }
  if (
    lower.includes("urgência") ||
    lower.includes("curta") ||
    lower.includes("nao informad") ||
    lower.includes("comparar preco")
  ) {
    return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400";
  }
  return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400";
}

export function truncate(text: string, maxLength: number): string {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

export function getVehicleImageFallback(): string {
  return "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?w=600&q=80";
}
