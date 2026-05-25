"""
Normalizes existing marca/modelo values in the DB.
Run once after deploying the normalizer:
    python scripts/patch_brands.py
"""
import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from app.scrapers.normalizer import normalize_brand, normalize_model

DB_PATH = PROJECT_ROOT / "deepcar.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT id, marca, modelo FROM vehicles")
rows = c.fetchall()

updated_brands = 0
updated_models = 0

for row in rows:
    vid = row["id"]
    old_brand = row["marca"]
    old_model = row["modelo"]

    new_brand = normalize_brand(old_brand)
    new_model = normalize_model(old_model)

    if new_brand != old_brand or new_model != old_model:
        c.execute(
            "UPDATE vehicles SET marca = ?, modelo = ? WHERE id = ?",
            (new_brand, new_model, vid),
        )
        if new_brand != old_brand:
            updated_brands += 1
        if new_model != old_model:
            updated_models += 1

conn.commit()
print(f"Updated {updated_brands} brand fields, {updated_models} model fields out of {len(rows)} records.")

# Show resulting distinct brands
c.execute("SELECT marca, COUNT(*) as n FROM vehicles GROUP BY marca ORDER BY n DESC LIMIT 40")
print("\nTop brands after normalization:")
for r in c.fetchall():
    print(f"  {r['marca']}: {r['n']}")

conn.close()
