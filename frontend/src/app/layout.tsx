import type { Metadata, Viewport } from "next";
import { Manrope, Sora } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

const BRAND_ICON_URL = "/DeepCar_Icon.png?v=20260525";
const MANIFEST_URL = "/manifest.json?v=20260525";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "DeepCar | Radar inteligente para compra de carros",
    template: "%s | DeepCar",
  },
  description:
    "Encontre carros usados e seminovos com leitura de score, contexto de preço e busca inteligente em múltiplas fontes.",
  keywords: ["carros", "veículos", "seminovos", "usados", "comprar carro", "melhor preço"],
  manifest: MANIFEST_URL,
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "DeepCar",
  },
  openGraph: {
    title: "DeepCar | Radar inteligente para compra de carros",
    description: "Busca profissional de veículos com score, insights e leitura rápida de mercado.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#edf3fb" },
    { media: "(prefers-color-scheme: dark)", color: "#050c15" },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <link rel="icon" href={BRAND_ICON_URL} type="image/png" sizes="1024x1024" />
        <link rel="apple-touch-icon" href={BRAND_ICON_URL} />
      </head>
      <body className={`${manrope.variable} ${sora.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
