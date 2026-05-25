import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

import app.scrapers.olx_scraper
import app.services.score_service
import app.services.fipe_service
import app.scrapers.scheduler
print("All imports OK")
