"""
Patch existing iCarros vehicles in the DB with full titles and versao.
Uses the listing page HTML (anchor title attributes) to get the full vehicle name.
Also patches photos if still only 1.

Strategy:
- Fetch the iCarros listing pages (same as scraper does)
- Parse anchor title attributes for full titles
- Update existing DB records
"""
import asyncio
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal, create_tables
from app.models.vehicle import Vehicle
from app.scrapers.icarros_scraper import ICarrosScraper


async def patch():
    await create_tables()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Vehicle.id, Vehicle.source_url, Vehicle.fotos, Vehicle.titulo, Vehicle.versao, Vehicle.marca, Vehicle.modelo, Vehicle.ano)
            .where(
                Vehicle.source_name == "iCarros",
                Vehicle.source_url.isnot(None),
            )
        )
        rows = result.all()

    print(f"iCarros vehicles in DB: {len(rows)}")

    # Build a map from source_url (clean) -> row
    url_map = {}
    for vid, url, fotos, titulo, versao, marca, modelo, ano in rows:
        clean = url.split("?")[0]
        url_map[clean] = {"id": vid, "fotos": fotos, "titulo": titulo, "versao": versao,
                          "marca": marca, "modelo": modelo, "ano": ano}

    # Fetch all listing pages and build title + photo data
    scraper = ICarrosScraper()
    headers = {
        "User-Agent": scraper._get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }

    title_anchor_re = re.compile(
        r'href="(/comprar/[^"?#]{10,})[^"]*"\s+title="([^"]{5,})"',
        re.IGNORECASE,
    )
    img_re = re.compile(
        r'<img[^>]+(?:src|data-src|data-lazy)="(https?://img\d+\.icarros\.com/[^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"',
        re.IGNORECASE,
    )
    card_re = re.compile(
        r'<a[^>]+href="(https?://www\.icarros\.com\.br/comprar/[^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    title_data: dict[str, dict] = {}  # clean_url -> {titulo, versao, fotos}

    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        for page_num in range(1, 10):
            try:
                r = await client.get(
                    f"https://www.icarros.com.br/ache/listaanuncios.jsp?pag={page_num}&ord=6",
                    headers=headers,
                )
                if r.status_code != 200:
                    print(f"Page {page_num}: status {r.status_code}, stopping")
                    break
                page_html = r.content.decode("utf-8", errors="replace")

                # Build JSON-LD block list for parsing
                vehicles_on_page = scraper._parse_html(page_html)

                found_count = 0
                for v in vehicles_on_page:
                    clean_url = (v.get("source_url") or "").split("?")[0]
                    if clean_url in url_map:
                        title_data[clean_url] = {
                            "titulo": v.get("titulo") or "",
                            "versao": v.get("versao") or "",
                            "fotos": v.get("fotos") or [],
                        }
                        found_count += 1

                print(f"Page {page_num}: found {found_count}/{len(vehicles_on_page)} vehicles matching DB")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Page {page_num} error: {e}")
                break

    print(f"\nMatched {len(title_data)} DB vehicles with listing data")

    patched = 0
    for clean_url, new_data in title_data.items():
        row = url_map[clean_url]
        updates = {}
        if new_data["titulo"] and new_data["titulo"] != row["titulo"]:
            updates["titulo"] = new_data["titulo"]
        if new_data["versao"] and new_data["versao"] != row["versao"]:
            updates["versao"] = new_data["versao"]
        if new_data["fotos"] and len(new_data["fotos"]) > len(row["fotos"] or []):
            updates["fotos"] = new_data["fotos"]

        if updates:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Vehicle).where(Vehicle.id == row["id"]).values(**updates)
                )
                await db.commit()
            patched += 1
            print(f"  Updated id={row['id']}: {updates.get('titulo', row['titulo'])}")

    print(f"\nDone. Updated {patched} records.")

    from app.core.cache import cache_delete_pattern
    await cache_delete_pattern("vehicle:*")
    await cache_delete_pattern("search:*")
    print("Cache invalidated.")


asyncio.run(patch())
