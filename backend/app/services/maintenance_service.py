import asyncio
import json
import logging
from typing import Optional

from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal, create_tables
from app.models.vehicle import Vehicle
from app.services.fipe_service import get_fipe_price
from app.services.score_service import calcular_score

logger = logging.getLogger(__name__)

DEFAULT_FIPE_DELAY_SECONDS = 2.0
_maintenance_lock = asyncio.Lock()


def _vehicle_payload(vehicle: Vehicle) -> dict:
    fotos = vehicle.fotos
    if isinstance(fotos, str):
        try:
            fotos = json.loads(fotos)
        except Exception:
            fotos = []

    return {
        "preco": vehicle.preco,
        "km": vehicle.km,
        "ano": vehicle.ano,
        "fotos": fotos if isinstance(fotos, list) else [],
        "descricao": vehicle.descricao,
        "vendedor_tipo": vehicle.vendedor_tipo,
    }


async def update_missing_fipe_prices(
    limit: Optional[int] = None,
    delay_seconds: float = DEFAULT_FIPE_DELAY_SECONDS,
) -> dict:
    async with _maintenance_lock:
        await create_tables()

        async with AsyncSessionLocal() as db:
            stmt = select(Vehicle).where(Vehicle.fipe_preco.is_(None)).order_by(Vehicle.id)
            if limit:
                stmt = stmt.limit(limit)
            result = await db.execute(stmt)
            vehicles = result.scalars().all()

        if not vehicles:
            logger.info("FIPE update: all vehicles already have FIPE prices")
            return {"processed": 0, "updated": 0, "not_found": 0}

        logger.info(
            "FIPE update starting for %s vehicles (delay=%ss)",
            len(vehicles),
            delay_seconds,
        )
        updated = 0
        not_found = 0

        for index, vehicle in enumerate(vehicles, 1):
            marca = vehicle.marca or ""
            modelo = vehicle.modelo or ""
            ano = vehicle.ano or 0

            if not marca or not modelo or not ano:
                not_found += 1
                continue

            logger.info("FIPE [%s/%s] %s %s %s", index, len(vehicles), marca, modelo, ano)
            fipe = await get_fipe_price(marca, modelo, ano)
            if fipe:
                new_score, new_insights = calcular_score(
                    _vehicle_payload(vehicle),
                    fipe_preco=fipe["preco"],
                )
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(Vehicle)
                        .where(Vehicle.id == vehicle.id)
                        .values(
                            fipe_preco=fipe["preco"],
                            score=new_score,
                            insights=new_insights,
                        )
                    )
                    await db.commit()
                updated += 1
            else:
                not_found += 1

            if delay_seconds > 0 and index < len(vehicles):
                await asyncio.sleep(delay_seconds)

        logger.info(
            "FIPE update finished: %s updated, %s not found",
            updated,
            not_found,
        )
        return {"processed": len(vehicles), "updated": updated, "not_found": not_found}


async def rescore_existing_vehicles(limit: Optional[int] = None) -> int:
    async with _maintenance_lock:
        await create_tables()

        async with AsyncSessionLocal() as db:
            stmt = select(Vehicle).order_by(Vehicle.id)
            if limit:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            vehicles = result.scalars().all()

            if not vehicles:
                logger.info("Rescore: no vehicles found to reprocess")
                return 0

            precos_por_modelo: dict[str, list[float]] = {}
            for vehicle in vehicles:
                if vehicle.preco and vehicle.preco > 0:
                    key = f"{vehicle.marca or ''}_{vehicle.modelo or ''}_{vehicle.ano or 0}"
                    precos_por_modelo.setdefault(key, []).append(vehicle.preco)

            medias = {
                key: sum(values) / len(values)
                for key, values in precos_por_modelo.items()
                if values
            }
            tamanhos_amostra = {
                key: len(values)
                for key, values in precos_por_modelo.items()
                if values
            }

            for vehicle in vehicles:
                key = f"{vehicle.marca or ''}_{vehicle.modelo or ''}_{vehicle.ano or 0}"
                score, insights = calcular_score(
                    _vehicle_payload(vehicle),
                    preco_medio_mercado=medias.get(key),
                    fipe_preco=vehicle.fipe_preco,
                    amostra_preco_size=tamanhos_amostra.get(key),
                )
                vehicle.score = score
                vehicle.insights = insights

            await db.commit()

        logger.info("Rescore finished: %s vehicles reprocessed", len(vehicles))
        return len(vehicles)