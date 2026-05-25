import sqlite3
from pathlib import Path

db_path = Path(r"c:\Users\Lenovo\Documents\Projetos\DeepCar\backend\deepcar.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()
print("olx_total", cur.execute("select count(*) from vehicles where source_name='OLX'").fetchone()[0])
print("olx_active", cur.execute("select count(*) from vehicles where source_name='OLX' and ativo=1").fetchone()[0])
print("all_total", cur.execute("select count(*) from vehicles").fetchone()[0])
print("all_active", cur.execute("select count(*) from vehicles where ativo=1").fetchone()[0])
conn.close()
