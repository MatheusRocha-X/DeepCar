"""
Atualiza preços FIPE de veículos sem fipe_preco no banco.

Uso: python scripts/update_fipe.py [limite]
  limite: número máximo de veículos a processar (padrão: 50)
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.maintenance_service import (
    DEFAULT_FIPE_DELAY_SECONDS,
    update_missing_fipe_prices,
)


async def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    result = await update_missing_fipe_prices(
        limit=limit,
        delay_seconds=DEFAULT_FIPE_DELAY_SECONDS,
    )

    if result["processed"] == 0:
        print("Todos os veículos já têm preço FIPE.")
        return

    print(
        f"Atualizado: {result['updated']} | Não encontrado: {result['not_found']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
