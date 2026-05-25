"""Quick test of the rewritten iCarros scraper."""
import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from app.scrapers.icarros_scraper import ICarrosScraper

async def main():
    scraper = ICarrosScraper(max_pages=2)
    results = await scraper.scrape()
    print(f"Total: {len(results)} vehicles")
    for v in results[:3]:
        print(f"  {v['titulo']} | {v['marca']} {v['modelo']} {v['ano']} | "
              f"R${v['preco']} | {v['km']}km | {v['combustivel']} | {v['cambio']}")
        print(f"  URL: {v['source_url']}")
        print(f"  Fotos: {v['fotos'][:1]}")
        print()

asyncio.run(main())
