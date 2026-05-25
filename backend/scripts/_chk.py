import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        r = await db.execute(text('SELECT source_name, COUNT(*) FROM vehicles GROUP BY source_name'))
        for row in r.fetchall():
            print(f'  {row[0]}: {row[1]}')
        r2 = await db.execute(text('SELECT COUNT(*) FROM vehicles'))
        print(f'  TOTAL: {r2.scalar()}')

asyncio.run(check())
