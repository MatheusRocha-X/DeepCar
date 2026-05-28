"use client";

import Image from "next/image";
import { useTheme } from "next-themes";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sun, Moon, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const BRAND_ICON_URL = "/DeepCar_Icon.png?v=20260525";

export function Header() {
  const { theme, setTheme } = useTheme();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  const navigation = [
    { href: "/", label: "Explorar", icon: Search },
  ];

  useEffect(() => {
    setMounted(true);
    const handleScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 px-4 pt-4 transition-all duration-300 sm:px-6",
        scrolled ? "translate-y-0" : "translate-y-0"
      )}
    >
      <div
        className={cn(
          "surface-panel mx-auto flex max-w-7xl items-center justify-between gap-3 rounded-[1.7rem] px-4 py-3 sm:px-5",
          scrolled ? "bg-[#090909]/78" : "bg-[#090909]/62"
        )}
      >
        <Link href="/" className="flex min-w-0 items-center gap-3">
          <div className="relative h-11 w-11 overflow-hidden rounded-2xl ring-1 ring-white/[0.06]">
            <Image
              src={BRAND_ICON_URL}
              alt="DeepCar"
              fill
              className="object-cover"
              sizes="44px"
              priority
              unoptimized
            />
          </div>
          <div className="min-w-0">
            <p className="truncate text-[0.62rem] font-semibold uppercase tracking-[0.34em] text-brand-200/70">
              Radar inteligente
            </p>
            <span className="font-display block truncate text-lg font-semibold text-white">
              DeepCar
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-2">
          <nav className="flex items-center gap-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "relative flex items-center gap-2 rounded-[1.1rem] border px-3.5 py-2.5 text-sm font-medium transition-all",
                    isActive
                      ? "border-white/[0.08] bg-white/[0.06] text-white shadow-[0_12px_30px_rgba(2,8,18,0.22)]"
                      : "border-transparent text-slate-400 hover:border-white/[0.06] hover:bg-white/[0.035] hover:text-white"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span className="hidden sm:inline">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {mounted && (
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="flex h-11 w-11 items-center justify-center rounded-[1.1rem] border border-white/[0.06] bg-white/[0.035] text-slate-300 transition-all hover:bg-white/[0.06] hover:text-white"
              aria-label="Alternar tema"
            >
              {theme === "dark" ? (
                <Sun className="h-5 w-5" />
              ) : (
                <Moon className="h-5 w-5" />
              )}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
