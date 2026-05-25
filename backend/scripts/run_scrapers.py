"""
Roda os scrapers reais e popula o banco de dados.
Uso: python scripts/run_scrapers.py [olx|icarros|all] [paginas]
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import create_tables
from app.services.scrape_service import ACTIVE_SCRAPERS, run_manual_scrapers


async def main():
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    print("Criando tabelas...")
    await create_tables()

    if target != "all" and target not in ACTIVE_SCRAPERS:
        print(f"Fonte desconhecida: {target}. Use: {', '.join(ACTIVE_SCRAPERS)} ou 'all'")
        sys.exit(1)

    result = await run_manual_scrapers(target=target, pages=pages)

    print(f"\n{'='*50}")
    print(f"  Scrape concluído: {target.upper()} ({pages} páginas)")
    print(f"{'='*50}")
    for name, saved in result["saved_by_source"].items():
        print(f"  {name.upper()}: {saved} veículos salvos")

    print(f"\n{'='*50}")
    print(f"  TOTAL SALVO NO BANCO: {result['total_saved']} veículos")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
