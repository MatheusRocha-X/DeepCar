from app.scrapers.olx_scraper import OLXScraper
from app.services.score_service import calcular_score, calcular_score_batch
from app.services.vehicle_service import (
    build_smart_scrape_display_query,
    build_smart_scrape_query,
    should_scrape_olx_for_filters,
    create_or_update_vehicle,
    has_meaningful_search_filters,
    vehicle_matches_filters,
)
from app.core.cache import cache_delete_pattern
from app.core.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, AsyncGenerator, Any
from datetime import datetime
from pathlib import Path
import logging
import asyncio
import subprocess
import sys
import json
import os

logger = logging.getLogger(__name__)


class ScraperScheduler:
    # Scrapers that are currently working and run on "all"
    ENABLED_SCRAPERS = {"olx"}

    # Cooldown between scrapes of the same query (seconds)
    SCRAPE_COOLDOWN = 1800  # 30 minutes
    MIN_PAGES_BEFORE_DISPLAY = 3
    SMART_SCRAPE_BATCH_PAGES = 2
    SMART_SCRAPE_BATCH_PAUSE_SECONDS = 1.0

    def __init__(self):
        self.scrapers = {
            "olx": OLXScraper,
        }
        self._status = {
            name: {
                "source": name,
                "status": "idle",
                "last_run": None,
                "total_collected": 0,
                "errors": 0,
            }
            for name in self.scrapers
        }
        # Debounce map: query_key → last scraped timestamp
        self._recent_scrapes: dict[str, float] = {}
        self._active_smart_scrapes: dict[str, asyncio.Task] = {}
        self._olx_workers: dict[str, subprocess.Popen] = {}
        self._query_progress: dict[str, dict] = {}

    def get_status(self):
        return list(self._status.values())

    def _idle_query_progress(self, query: str) -> dict:
        return {
            "query": query,
            "status": "idle",
            "running": False,
            "done": False,
            "pages_scraped": 0,
            "saved_total": 0,
            "display_ready": False,
            "min_pages_before_display": self.MIN_PAGES_BEFORE_DISPLAY,
            "task_running": False,
            "worker_running": False,
            "started_at": None,
            "updated_at": None,
        }

    def _set_query_progress(self, query_key: str, query: str, **updates) -> dict:
        now = datetime.now()
        progress = self._query_progress.get(query_key)
        if not progress:
            progress = self._idle_query_progress(query)
            progress["started_at"] = now

        progress.update(updates)
        progress["query"] = query
        progress["min_pages_before_display"] = self.MIN_PAGES_BEFORE_DISPLAY

        pages_scraped = progress.get("pages_scraped", 0)
        worker_running = bool(progress.get("worker_running"))
        display_ready = bool(
            progress.get("display_ready")
            or worker_running
            or pages_scraped >= self.MIN_PAGES_BEFORE_DISPLAY
            or progress.get("done")
        )
        progress["display_ready"] = display_ready
        progress["updated_at"] = now

        self._query_progress[query_key] = progress
        return progress

    def _query_key(self, query: str) -> str:
        return " ".join(query.split()).strip().lower()

    def _build_query_from_filters(self, filters) -> str:
        return build_smart_scrape_display_query(filters)

    def _build_scrape_query_from_filters(self, filters) -> str:
        return build_smart_scrape_query(filters)

    def _prune_recent_scrapes(self, now: float) -> None:
        cutoff = now - self.SCRAPE_COOLDOWN * 4
        self._recent_scrapes = {k: v for k, v in self._recent_scrapes.items() if v > cutoff}

    def _reap_finished_olx_workers(self) -> None:
        self._olx_workers = {
            key: proc for key, proc in self._olx_workers.items() if proc.poll() is None
        }

    def get_query_progress(self, query: str) -> dict:
        query_key = self._query_key(query)
        if not query_key:
            return self._idle_query_progress(query)

        self._reap_finished_olx_workers()

        progress = self._query_progress.get(query_key)
        if not progress:
            return self._idle_query_progress(query)

        task = self._active_smart_scrapes.get(query_key)
        task_running = bool(task and not task.done())
        worker_running = bool(self._olx_workers.get(query_key))
        running = task_running or worker_running

        if running:
            return self._set_query_progress(
                query_key,
                progress.get("query", query),
                status="running",
                running=True,
                done=False,
                task_running=task_running,
                worker_running=worker_running,
            )

        if progress.get("status") == "running":
            return self._set_query_progress(
                query_key,
                progress.get("query", query),
                status="completed",
                running=False,
                done=True,
                task_running=False,
                worker_running=False,
            )

        return self._set_query_progress(
            query_key,
            progress.get("query", query),
            running=False,
            task_running=False,
            worker_running=False,
        )

    def _finalize_smart_scrape(self, query_key: str, task: asyncio.Task) -> None:
        current = self._active_smart_scrapes.get(query_key)
        if current is task:
            self._active_smart_scrapes.pop(query_key, None)
        try:
            task.result()
        except asyncio.CancelledError:
            logger.info(f"Smart scrape cancelled for '{query_key}'")
            progress = self._query_progress.get(query_key)
            if progress:
                self._set_query_progress(
                    query_key,
                    progress.get("query", query_key),
                    status="cancelled",
                    running=False,
                    done=True,
                    task_running=False,
                )
        except Exception as e:
            logger.error(f"Smart scrape task failed for '{query_key}': {e}")
            progress = self._query_progress.get(query_key)
            if progress:
                self._set_query_progress(
                    query_key,
                    progress.get("query", query_key),
                    status="error",
                    running=False,
                    done=True,
                    task_running=False,
                )

    def start_smart_scrape_for_filters(self, filters) -> bool:
        if not has_meaningful_search_filters(filters) or not should_scrape_olx_for_filters(filters):
            return False

        query = self._build_query_from_filters(filters)
        query_key = self._query_key(query)
        if not query_key:
            return False

        now = datetime.now().timestamp()
        last = self._recent_scrapes.get(query_key, 0.0)
        if now - last < self.SCRAPE_COOLDOWN:
            return False

        current = self._active_smart_scrapes.get(query_key)
        if current and not current.done():
            return False

        self._set_query_progress(
            query_key,
            query,
            status="running",
            running=True,
            done=False,
            pages_scraped=0,
            saved_total=0,
            task_running=True,
            worker_running=False,
            display_ready=False,
            started_at=datetime.now(),
        )

        task = asyncio.create_task(self.smart_scrape_for_filters(filters))
        self._active_smart_scrapes[query_key] = task
        task.add_done_callback(lambda t, key=query_key: self._finalize_smart_scrape(key, t))
        return True

    def cancel_query_scrape(self, query: str) -> dict:
        query_key = self._query_key(query)
        task_cancelled = False
        worker_cancelled = False

        task = self._active_smart_scrapes.pop(query_key, None)
        if task and not task.done():
            task.cancel()
            task_cancelled = True

        self._reap_finished_olx_workers()
        worker = self._olx_workers.pop(query_key, None)
        if worker and worker.poll() is None:
            try:
                worker.terminate()
                worker_cancelled = True
            except Exception as e:
                logger.warning(f"Failed to terminate OLX worker for '{query}': {e}")

        self._recent_scrapes.pop(query_key, None)

        progress = self._query_progress.get(query_key)
        if progress:
            self._set_query_progress(
                query_key,
                progress.get("query", query),
                status="cancelled",
                running=False,
                done=True,
                task_running=False,
                worker_running=False,
            )

        if task_cancelled or worker_cancelled:
            logger.info(f"Cancelled scrape for '{query}' (task={task_cancelled}, worker={worker_cancelled})")

        return {
            "query": query,
            "task_cancelled": task_cancelled,
            "worker_cancelled": worker_cancelled,
        }

    async def run_source(self, source: str, db: AsyncSession):
        if source == "all":
            for name in self.ENABLED_SCRAPERS:
                await self._run_single(name, db)
        elif source in self.scrapers:
            await self._run_single(source, db)

    async def smart_scrape_for_filters(self, filters) -> int:
        """
                Background scrape triggered by a user search.
                Builds a query from filters and runs OLX in a separate worker
                process so user searches keep surfacing vehicles even when
                iCarros is blocked by human verification.
        Debounced: same query won't re-trigger within SCRAPE_COOLDOWN seconds.
        """
        if not has_meaningful_search_filters(filters) or not should_scrape_olx_for_filters(filters):
            return 0

        query = self._build_query_from_filters(filters)
        scrape_query = self._build_scrape_query_from_filters(filters)
        query_key = self._query_key(query)
        if not query_key or not scrape_query:
            return 0

        # Debounce check
        now = datetime.now().timestamp()
        last = self._recent_scrapes.get(query_key, 0.0)
        if now - last < self.SCRAPE_COOLDOWN:
            logger.debug(f"Smart scrape debounced for '{query}' ({int(self.SCRAPE_COOLDOWN - (now - last))}s left)")
            return 0

        self._recent_scrapes[query_key] = now
        self._prune_recent_scrapes(now)

        logger.info(f"Smart scrape starting for filters: '{query}' via query '{scrape_query}'")
        progress = self._query_progress.get(query_key)
        total_saved = int(progress.get("saved_total", 0)) if progress else 0
        pages_scraped = int(progress.get("pages_scraped", 0)) if progress else 0
        next_page = pages_scraped + 1

        try:
            while True:
                batch = await self._run_olx_query_worker_batch(
                    scrape_query,
                    start_page=next_page,
                    max_pages=self.SMART_SCRAPE_BATCH_PAGES,
                    filters=filters,
                    progress_query=query,
                )

                batch_pages = max(
                    1,
                    int(batch.get("pages", self.SMART_SCRAPE_BATCH_PAGES) or self.SMART_SCRAPE_BATCH_PAGES),
                )
                batch_saved = max(0, int(batch.get("saved", 0) or 0))
                batch_collected = max(0, int(batch.get("collected", 0) or 0))

                pages_scraped += batch_pages
                total_saved += batch_saved

                if batch_saved:
                    await cache_delete_pattern("search:*")
                    await cache_delete_pattern("filter_options")

                self._set_query_progress(
                    query_key,
                    query,
                    status="running",
                    running=True,
                    done=False,
                    pages_scraped=pages_scraped,
                    saved_total=total_saved,
                    task_running=True,
                    worker_running=False,
                )

                if batch_collected == 0:
                    logger.info(
                        "Smart scrape reached end of OLX results for '%s' at page %s",
                        query,
                        next_page,
                    )
                    break

                next_page += batch_pages

                if self.SMART_SCRAPE_BATCH_PAUSE_SECONDS > 0:
                    await asyncio.sleep(self.SMART_SCRAPE_BATCH_PAUSE_SECONDS)

            self._set_query_progress(
                query_key,
                query,
                status="completed",
                running=False,
                done=True,
                pages_scraped=pages_scraped,
                saved_total=total_saved,
                task_running=False,
                worker_running=False,
            )
        except asyncio.CancelledError:
            logger.info(f"Smart scrape stopping for '{query}'")
            raise
        except Exception as e:
            logger.error(f"Smart scrape OLX error: {e}")
            self._set_query_progress(
                query_key,
                query,
                status="error",
                running=False,
                done=True,
                pages_scraped=pages_scraped,
                saved_total=total_saved,
                task_running=False,
                worker_running=False,
            )

        return total_saved

        """
        Fast targeted scrape for a specific query (1-2 pages, OLX only).
        Used for real-time search enrichment.
        Returns number of new vehicles saved.
        """
        from app.scrapers.olx_scraper import OLXScraper as _OLX
        key = f"live:{query}"
        self._status[key] = {"source": "live", "status": "running", "query": query}

        try:
            scraper = _OLX(max_pages=2, query=query)
            raw = await scraper.scrape()
            valid = [v for v in raw if v.get("titulo") and v.get("source_url") and v.get("modelo")]

            scored = calcular_score_batch(valid, calcular_media_por_modelo=True)

            saved = 0
            for vehicle_data in scored:
                try:
                    async with AsyncSessionLocal() as session:
                        await create_or_update_vehicle(session, vehicle_data)
                    saved += 1
                except Exception as e:
                    logger.warning(f"Live scrape save error: {e}")

            if saved:
                await cache_delete_pattern("search:*")

            self._status[key]["status"] = "completed"
            self._status[key]["saved"] = saved
            logger.info(f"Live scrape '{query}': {saved} vehicles saved")
            return saved

        except Exception as e:
            logger.error(f"Live scrape error: {e}")
            self._status[key]["status"] = "error"
            return 0

    async def _run_single(self, name: str, db: AsyncSession):
        self._status[name]["status"] = "running"
        self._status[name]["errors"] = 0

        try:
            from app.services.scrape_service import run_single_source_scraper

            logger.info(f"Starting scraper: {name}")
            pages = self.scrapers[name]().max_pages
            result = await run_single_source_scraper(name, pages=pages)
            saved_count = int(result.get("saved", 0) or 0)

            await cache_delete_pattern("search:*")
            await cache_delete_pattern("filter_options")

            self._status[name]["status"] = "completed"
            self._status[name]["last_run"] = datetime.now()
            self._status[name]["total_collected"] = saved_count
            logger.info(f"Scraper {name} finished: {saved_count} vehicles saved")

        except Exception as e:
            logger.error(f"Scraper {name} failed: {e}")
            self._status[name]["status"] = "error"
            self._status[name]["errors"] += 1

    async def _run_olx_query_worker_batch(
        self,
        query: str,
        start_page: int = 1,
        max_pages: int = 2,
        filters=None,
        progress_query: Optional[str] = None,
    ) -> dict[str, Any]:
        query_key = self._query_key(progress_query or query)
        batch_result: dict[str, Any] = {
            "query": query,
            "start_page": start_page,
            "pages": max_pages,
            "saved": 0,
            "matched": 0,
            "collected": 0,
        }

        process = self._spawn_olx_query_worker(
            query,
            max_pages=max_pages,
            start_page=start_page,
            filters=filters,
            progress_query=progress_query,
        )
        if process is None:
            return batch_result

        output = ""
        try:
            stdout, _ = await asyncio.to_thread(process.communicate)
            output = stdout or ""
        except asyncio.CancelledError:
            if process.poll() is None:
                try:
                    process.terminate()
                except Exception:
                    pass
            raise
        finally:
            current = self._olx_workers.get(query_key)
            if current is process and process.poll() is not None:
                self._olx_workers.pop(query_key, None)

        for line in reversed(output.splitlines()):
            candidate = line.strip()
            if not candidate:
                continue
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                batch_result.update(payload)
                break

        if process.returncode not in (0, None):
            logger.warning(
                "OLX worker batch failed for '%s' starting at page %s (exit=%s)",
                progress_query or query,
                start_page,
                process.returncode,
            )

        return batch_result

    def _spawn_olx_query_worker(
        self,
        query: str,
        max_pages: int = 2,
        start_page: int = 1,
        filters=None,
        progress_query: Optional[str] = None,
    ) -> Optional[subprocess.Popen]:
        query_key = self._query_key(progress_query or query)
        if not query_key:
            return None

        worker_script = Path(__file__).resolve().parents[2] / "olx_query_worker.py"
        if not worker_script.exists():
            logger.error(f"OLX worker script not found: {worker_script}")
            return None

        try:
            self._reap_finished_olx_workers()
            current = self._olx_workers.get(query_key)
            if current and current.poll() is None:
                return current

            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            worker_args = [sys.executable, str(worker_script), query, str(max_pages), str(start_page)]
            if filters is not None:
                worker_args.append(filters.model_dump_json(exclude_none=True))
            worker_env = os.environ.copy()
            worker_env["OLX_WORKER_RESULT_JSON"] = "1"
            process = subprocess.Popen(
                worker_args,
                cwd=str(worker_script.parent),
                creationflags=creationflags,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=worker_env,
            )
            self._olx_workers[query_key] = process
            logger.info(
                "Started OLX worker for filters '%s' via query '%s' (pages %s-%s)",
                progress_query or query,
                query,
                start_page,
                start_page + max_pages - 1,
            )
            return process
        except Exception as e:
            logger.error(f"Failed to start OLX worker for '{query}': {e}")
            return None

    async def stream_live_scrape(self, query: str) -> AsyncGenerator[dict, None]:
        """
        Async generator for real-time scraping via SSE.
        If smart_scrape_for_filters is already handling this query (debounce hit),
        returns immediately — no need to double-scrape OLX.
        Otherwise runs a small OLX query scrape to enrich the DB quickly.
        Yields {"source": str, "saved": int} per page batch, then {"done": True, "total": int}.
        """
        # Reuse the same debounce: if smart_scrape already claimed this query,
        # skip scraping here to avoid hitting OLX simultaneously.
        now = datetime.now().timestamp()
        last = self._recent_scrapes.get(self._query_key(query), 0.0)
        if now - last < self.SCRAPE_COOLDOWN:
            yield {"done": True, "total": 0}
            return

        total_saved = 0
        try:
            scraper = OLXScraper(max_pages=2, query=query)
            raw = await scraper.scrape(max_pages=2)
            valid = [
                v for v in raw
                if v.get("titulo") and v.get("source_url") and v.get("modelo")
            ]
            if valid:
                scored = calcular_score_batch(valid, calcular_media_por_modelo=True)
                for vehicle_data in scored:
                    try:
                        async with AsyncSessionLocal() as session:
                            await create_or_update_vehicle(session, vehicle_data)
                        total_saved += 1
                    except Exception as e:
                        logger.warning(f"Stream save error (OLX): {e}")

                if total_saved > 0:
                    yield {"source": "OLX", "saved": total_saved}
        except Exception as e:
            logger.error(f"Stream live scrape error: {e}")

        if total_saved > 0:
            await cache_delete_pattern("search:*")
            await cache_delete_pattern("filter_options")

        yield {"done": True, "total": total_saved}


scraper_scheduler = ScraperScheduler()
