"""
Recalcula score e insights dos veículos já salvos no banco.

Uso:
    py -3 scripts/rescore_existing_vehicles.py [limite]

Se `limite` for informado, processa apenas os N primeiros veículos.
"""
import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.maintenance_service import rescore_existing_vehicles


async def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    updated = await rescore_existing_vehicles(limit=limit)

    if updated == 0:
        print("Nenhum veículo encontrado para reprocessar.")
        return

    print(f"Reprocessados {updated} veículos.")


if __name__ == "__main__":
    asyncio.run(main())