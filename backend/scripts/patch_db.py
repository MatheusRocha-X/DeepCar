from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
conn = sqlite3.connect(PROJECT_ROOT / 'deepcar.db')
c = conn.cursor()
# Add fipe_preco column if it doesn't exist
try:
    c.execute('ALTER TABLE vehicles ADD COLUMN fipe_preco REAL')
    conn.commit()
    print('Added fipe_preco column')
except sqlite3.OperationalError as e:
    print('Column already exists or error:', e)
# Clear old OLX records with bad data (km=NULL and ano=NULL)
c.execute("DELETE FROM vehicles WHERE source_name='OLX'")
deleted = c.rowcount
conn.commit()
print(f'Deleted {deleted} bad OLX records')
c.execute("SELECT source_name, COUNT(*) FROM vehicles GROUP BY source_name")
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]} records')
conn.close()
