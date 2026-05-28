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

export function getVehicleImageFallback(): string {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 720" role="img" aria-label="Sem foto disponivel">
      <defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#08111c" />
          <stop offset="100%" stop-color="#12263a" />
        </linearGradient>
        <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#17324b" stop-opacity="0.9" />
          <stop offset="100%" stop-color="#0e1f30" stop-opacity="0.98" />
        </linearGradient>
      </defs>
      <rect width="1200" height="720" fill="url(#bg)" />
      <circle cx="1010" cy="120" r="180" fill="#38bdf8" fill-opacity="0.14" />
      <circle cx="180" cy="620" r="220" fill="#14b8a6" fill-opacity="0.1" />
      <rect x="120" y="120" width="960" height="480" rx="40" fill="url(#panel)" stroke="#7dd3fc" stroke-opacity="0.18" />
      <g fill="none" stroke="#cbd5e1" stroke-linecap="round" stroke-linejoin="round">
        <path d="M310 436h64l62-106c12-22 34-36 59-36h176c28 0 55 13 73 35l56 69h62c48 0 86 39 86 86v12H248v-23c0-20 7-38 18-53 11-14 27-24 44-24z" stroke-width="22" />
        <circle cx="425" cy="498" r="44" stroke-width="22" />
        <circle cx="806" cy="498" r="44" stroke-width="22" />
        <path d="M458 360h232" stroke-width="18" opacity="0.85" />
        <path d="M740 360h95" stroke-width="18" opacity="0.75" />
      </g>
      <text x="600" y="230" text-anchor="middle" fill="#e2e8f0" font-family="Segoe UI, Arial, sans-serif" font-size="42" font-weight="700" letter-spacing="6">DEEPCAR</text>
      <text x="600" y="278" text-anchor="middle" fill="#93c5fd" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="600" letter-spacing="5">IMAGEM INDISPONIVEL</text>
      <text x="600" y="565" text-anchor="middle" fill="#94a3b8" font-family="Segoe UI, Arial, sans-serif" font-size="24">O anuncio nao entregou uma foto valida agora.</text>
    </svg>`;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}
