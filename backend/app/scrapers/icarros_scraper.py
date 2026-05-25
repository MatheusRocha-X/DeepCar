from app.scrapers.base_scraper import BaseScraper, BaseVehicleData
from typing import List, Optional
import logging
import re
import json
import html
import asyncio
import httpx
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class ICarrosScraper(BaseScraper):
    BASE_URL = "https://www.icarros.com.br/ache/listaanuncios.jsp"
    USED_URL = "https://www.icarros.com.br/comprar/usados"
    BASE_SITE = "https://www.icarros.com.br"
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    RETRYABLE_STATUS_CODES = {403, 405, 408, 425, 429, 500, 502, 503, 504}

    def __init__(self, max_pages: int = 10, query: Optional[str] = None, start_page: int = 1):
        super().__init__("iCarros", max_pages)
        self.query = query
        self.start_page = max(1, start_page)

    def _build_url(self, page_num: int) -> str:
        q = quote_plus((self.query or "carro").strip() or "carro")
        return f"{self.BASE_URL}?pag={page_num}&ord=6&q={q}"

    def _build_headers(self, referer: Optional[str] = None) -> dict:
        headers = {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }

        if referer:
            headers["Referer"] = referer

        return headers

    def _create_client(self, referer: Optional[str] = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            follow_redirects=True,
            timeout=15,
            headers=self._build_headers(referer=referer),
        )

    async def _bootstrap_session(self, client: httpx.AsyncClient) -> None:
        for url in (self.BASE_SITE, self.USED_URL):
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    self.logger.debug(f"iCarros bootstrap {url} returned {response.status_code}")
                await self._random_delay(250, 500)
            except Exception as e:
                self.logger.debug(f"iCarros bootstrap {url} error: {e}")

    async def _get_listing_page(
        self,
        url: str,
        *,
        context: str,
        max_attempts: int = 3,
    ) -> httpx.Response:
        last_response: Optional[httpx.Response] = None
        for attempt in range(1, max_attempts + 1):
            try:
                async with self._create_client(referer=self.USED_URL) as client:
                    await self._bootstrap_session(client)
                    response = await client.get(url)
            except httpx.RequestError as e:
                if attempt == max_attempts:
                    raise
                self.logger.warning(f"{context} request error on attempt {attempt}/{max_attempts}: {e}")
                await self._random_delay(1200 * attempt, 1800 * attempt)
                continue

            if response.status_code == 200:
                return response

            last_response = response
            if response.status_code not in self.RETRYABLE_STATUS_CODES or attempt == max_attempts:
                return response

            self.logger.warning(
                f"{context} status {response.status_code} on attempt {attempt}/{max_attempts}; retrying"
            )
            await self._random_delay(1200 * attempt, 1800 * attempt)

        if last_response is None:
            raise RuntimeError(f"{context} failed without a response")
        return last_response

    async def scrape(self, max_pages: Optional[int] = None) -> List[dict]:
        pages_limit = max_pages or self.max_pages
        vehicles = []

        async with self._create_client(referer=self.USED_URL) as client:
            sem = asyncio.Semaphore(5)  # max 5 concurrent detail-page fetches
            for page_num in range(self.start_page, self.start_page + pages_limit):
                url = self._build_url(page_num)
                self.logger.info(f"iCarros scraping page {page_num}: {url}")
                try:
                    r = await self._get_listing_page(url, context=f"iCarros page {page_num}")
                    if r.status_code != 200:
                        self.logger.warning(f"iCarros page {page_num} status {r.status_code}")
                        break
                    # Force UTF-8 decoding regardless of Content-Type charset header
                    html_text = r.content.decode("utf-8", errors="replace")
                    page_vehicles = self._parse_html(html_text)
                    if not page_vehicles:
                        self.logger.info(f"iCarros page {page_num}: no vehicles, stopping")
                        break
                    # Enrich with full photo sets from detail pages
                    await self._enrich_photos(client, page_vehicles, sem)
                    vehicles.extend(page_vehicles)
                    self.logger.info(f"iCarros page {page_num}: {len(page_vehicles)} vehicles")
                    await self._random_delay(800, 1500)
                except Exception as e:
                    self.logger.error(f"iCarros page {page_num} error: {e}")
                    break

        self.logger.info(f"iCarros collected {len(vehicles)} vehicles total")
        return vehicles

    async def scrape_stream(self, max_pages: int = 2):
        """Async generator: yields List[dict] per page as they are scraped."""
        async with self._create_client(referer=self.USED_URL) as client:
            sem = asyncio.Semaphore(5)
            for page_num in range(self.start_page, self.start_page + max_pages):
                url = self._build_url(page_num)
                self.logger.info(f"iCarros stream page {page_num}: {url}")
                page_vehicles = []
                try:
                    r = await self._get_listing_page(url, context=f"iCarros stream page {page_num}")
                    if r.status_code != 200:
                        self.logger.warning(f"iCarros stream page {page_num} status {r.status_code}")
                        break
                    html_text = r.content.decode("utf-8", errors="replace")
                    page_vehicles = self._parse_html(html_text)
                    if not page_vehicles:
                        break
                    await self._enrich_photos(client, page_vehicles, sem)
                    self.logger.info(f"iCarros stream page {page_num}: {len(page_vehicles)} vehicles")
                    await self._random_delay(800, 1500)
                except Exception as e:
                    self.logger.error(f"iCarros stream page {page_num} error: {e}")
                    break
                yield page_vehicles

    async def _fetch_detail_photos(self, client: httpx.AsyncClient, detail_url: str) -> dict:
        """Fetch vehicle detail page and extract photos, full titulo, and versao.
        Returns a dict with keys: fotos, titulo, versao (any may be empty/None).
        """
        result: dict = {"fotos": [], "titulo": None, "versao": None}
        try:
            r = await client.get(detail_url, timeout=12)
            if r.status_code != 200:
                return result
            page = r.content.decode("utf-8", errors="replace")

            jld = re.findall(
                r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
                page, re.DOTALL | re.IGNORECASE,
            )
            for b in jld:
                try:
                    d = json.loads(b)
                    if d.get("@type") != "Vehicle":
                        continue

                    # Full title and version
                    result["titulo"] = d.get("name", "").strip() or None
                    result["versao"] = d.get("vehicleConfiguration", "").strip() or None

                    # Photos
                    imgs = d.get("image", [])
                    photos = []
                    items = imgs if isinstance(imgs, list) else [imgs]
                    for item in items:
                        if isinstance(item, dict):
                            url = item.get("contentUrl", "")
                        elif isinstance(item, str):
                            url = item
                        else:
                            continue
                        # iCarros truncates extensions in JSON-LD — add .jpg
                        if url and not re.search(r'\.(jpg|jpeg|webp|png)(\?|$)', url, re.I):
                            url = url.rstrip(".") + ".jpg"
                        if url.startswith("http"):
                            photos.append(url)
                    if photos:
                        result["fotos"] = photos
                    break  # first Vehicle block is enough
                except Exception:
                    pass
        except Exception as e:
            self.logger.debug(f"Detail fetch error {detail_url}: {e}")
        return result

    async def _enrich_photos(self, client: httpx.AsyncClient, vehicles: List[dict], sem: asyncio.Semaphore) -> None:
        """Concurrently fetch detail pages and enrich photos, titulo and versao in-place."""
        async def _enrich_one(v: dict) -> None:
            url = v.get("source_url", "")
            if not url:
                return
            clean = url.split("?")[0]
            async with sem:
                detail = await self._fetch_detail_photos(client, clean)
                if detail["fotos"]:
                    v["fotos"] = detail["fotos"]
                if detail["titulo"]:
                    v["titulo"] = detail["titulo"]
                if detail["versao"]:
                    v["versao"] = detail["versao"]

        await asyncio.gather(*[_enrich_one(v) for v in vehicles], return_exceptions=True)

    def _parse_html(self, html_text: str) -> List[dict]:
        """Extract vehicles from iCarros HTML via JSON-LD, then enrich with extra images."""
        vehicles = []

        # --- 1) JSON-LD Vehicle blocks ---
        json_ld_blocks = re.findall(
            r'<script[^>]+type="application/ld\+json"[^>]*>(.+?)</script>',
            html_text, re.DOTALL | re.IGNORECASE
        )

        # --- 2) Build a map of source_url -> full title and extra images from anchor tags ---
        # iCarros renders anchors like:
        #   <a href="/comprar/{city}/{brand}/{model}/{year}/d{id}?..." title="Brand Model Version">
        # The title attribute contains the full vehicle name with version/trim level.
        extra_images: dict[str, list] = {}
        title_map: dict[str, str] = {}

        # Match href="/comprar/..." immediately followed by title="..." (the iCarros pattern)
        title_anchor_re = re.compile(
            r'href="(/comprar/[^"?#]{10,})[^"]*"\s+title="([^"]{5,})"',
            re.IGNORECASE,
        )
        for m in title_anchor_re.finditer(html_text):
            rel_url = m.group(1)
            abs_url = f"https://www.icarros.com.br{rel_url}"
            candidate_title = html.unescape(m.group(2).strip())
            # Keep the longest title found for this URL
            if len(candidate_title) > len(title_map.get(abs_url, "")):
                title_map[abs_url] = candidate_title

        card_pattern = re.compile(
            r'<a[^>]+href="(https?://www\.icarros\.com\.br/[^"]+)"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        img_pattern = re.compile(
            r'<img[^>]+(?:src|data-src|data-lazy)="(https?://[^"]+\.(?:jpg|jpeg|webp|png)[^"]*)"',
            re.IGNORECASE,
        )
        for m in card_pattern.finditer(html_text):
            url = m.group(1).split("?")[0]
            imgs = img_pattern.findall(m.group(2))
            if imgs:
                extra_images[url] = list(dict.fromkeys(imgs))

        for block in json_ld_blocks:
            try:
                data = json.loads(block)
                if data.get("@type") == "Vehicle":
                    v = self._parse_vehicle_jsonld(data)
                    if v and v.is_valid():
                        if v.source_url:
                            clean_url = v.source_url.split("?")[0]
                            # Use anchor title for richer titulo (has full version)
                            anchor_title = title_map.get(clean_url, "")
                            if anchor_title and len(anchor_title) > len(v.titulo or ""):
                                # iCarros anchor title format: "{Brand} {Model} {Model} {TrimLevel}"
                                # The version starts with a duplicate of the model name.
                                # We strip the leading "{Brand} {Model} {Model} " to get
                                # a clean TrimLevel, then rebuild: "{Brand} {Model} {TrimLevel}"
                                prefix = f"{v.marca} {v.modelo}"
                                if anchor_title.lower().startswith(prefix.lower()):
                                    after_prefix = anchor_title[len(prefix):].strip()
                                    # Remove duplicate model name at start of after_prefix
                                    if after_prefix.lower().startswith(v.modelo.lower()):
                                        trim_level = after_prefix[len(v.modelo):].strip()
                                    else:
                                        trim_level = after_prefix
                                    v.versao = trim_level
                                    v.titulo = f"{prefix} {trim_level}".strip()
                                else:
                                    v.titulo = anchor_title
                            # Append year to titulo if not already present
                            if v.ano and str(v.ano) not in (v.titulo or ""):
                                v.titulo = f"{v.titulo} {v.ano}".strip()
                            # Enrich with extra images found in HTML
                            more = extra_images.get(clean_url, [])
                            if more and len(more) > len(v.fotos):
                                v.fotos = more
                        vehicles.append(v.to_dict())
            except Exception as e:
                self.logger.debug(f"JSON-LD parse error: {e}")
        return vehicles

    def _parse_vehicle_jsonld(self, data: dict) -> Optional[BaseVehicleData]:
        v = BaseVehicleData()
        v.source_name = "iCarros"

        try:
            v.titulo = data.get("name", "").strip()

            brand = data.get("brand", {})
            v.marca = brand.get("name", "").strip() if isinstance(brand, dict) else str(brand).strip()
            v.modelo = data.get("model", "").strip()

            year_str = data.get("vehicleModelDate", "")
            if year_str:
                v.ano = self._parse_ano(year_str)

            mileage = data.get("mileageFromOdometer", {})
            if isinstance(mileage, dict):
                km_raw = str(mileage.get("value", "")).strip()
                # Handle "45.233 Km" format (Brazilian dot-as-thousands-separator)
                km_digits = re.sub(r'[^\d]', '', km_raw.split(" ")[0])
                if km_digits:
                    v.km = int(km_digits)
                else:
                    v.km = 0

            fuel = data.get("fuelType", "")
            if fuel:
                v.combustivel = self._normalize_combustivel(fuel)

            transmission = data.get("vehicleTransmission", "")
            if transmission:
                v.cambio = self._normalize_cambio(transmission)

            offers = data.get("offers", {})
            if isinstance(offers, dict):
                price_str = str(offers.get("price", "")).strip()
                if price_str and price_str.replace(".", "").isdigit():
                    price = float(price_str)
                    if 1000 <= price <= 10_000_000:
                        v.preco = price

                offer_url = offers.get("url", "")
                if offer_url:
                    # Unescape HTML entities (e.g. &amp; -> &)
                    offer_url = html.unescape(offer_url)
                    if offer_url.startswith("http"):
                        v.source_url = offer_url
                    else:
                        v.source_url = f"{self.BASE_SITE}{offer_url}"
                    # Strip tracking params to keep URL clean
                    v.source_url = re.sub(r'[?&](pos|hfv|financiamento)=[^&]*', '', v.source_url)
                    v.source_url = v.source_url.rstrip("?&")

            images = data.get("image", [])
            if isinstance(images, list) and images:
                v.fotos = [img for img in images if isinstance(img, str) and img.startswith("http")]
            elif isinstance(images, str) and images.startswith("http"):
                v.fotos = [images]

            # Extract city/state from source URL: /comprar/{city}-{state-uf}/...
            if v.source_url:
                m = re.search(r'/comprar/([a-z0-9-]+)-([a-z]{2})/', v.source_url)
                if m:
                    city_slug = m.group(1).replace("-", " ").title()
                    v.cidade = city_slug
                    v.estado = m.group(2).upper()

        except Exception as e:
            self.logger.warning(f"iCarros JSON-LD parse error: {e}")
            return None

        return v
