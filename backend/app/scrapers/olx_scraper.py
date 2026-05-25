from app.scrapers.base_scraper import BaseScraper, BaseVehicleData
from typing import List, Optional
from urllib.parse import urlencode
import logging
import re
import json

logger = logging.getLogger(__name__)


class OLXScraper(BaseScraper):
    BASE_URL = "https://www.olx.com.br/autos-e-pecas/carros-vans-e-utilitarios"

    def __init__(
        self,
        max_pages: int = 10,
        query: Optional[str] = None,
        start_page: int = 1,
        extra_query_params: Optional[dict[str, str]] = None,
        base_urls: Optional[list[str]] = None,
    ):
        super().__init__("OLX", max_pages)
        self.query = query
        self.start_page = max(1, start_page)
        self.extra_query_params = {k: str(v) for k, v in (extra_query_params or {}).items() if v not in (None, "")}
        self.base_urls = [url.rstrip("/") for url in (base_urls or [self.BASE_URL]) if url]

    def _build_listing_url(self, page_num: int, base_url: Optional[str] = None) -> str:
        params = {"o": str(page_num), **self.extra_query_params}
        if self.query:
            params["q"] = self.query
        target_base_url = (base_url or self.BASE_URL).rstrip("/")
        return f"{target_base_url}?{urlencode(params)}"

    async def scrape(self, max_pages: Optional[int] = None) -> List[dict]:
        from playwright.async_api import async_playwright

        pages_limit = max_pages or self.max_pages
        vehicles = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    user_agent=self._get_random_user_agent(),
                    viewport={"width": 1366, "height": 768},
                    locale="pt-BR",
                )
                page = await context.new_page()

                for base_url in self.base_urls:
                    for page_num in range(self.start_page, self.start_page + pages_limit):
                        url = self._build_listing_url(page_num, base_url=base_url)
                        self.logger.info(f"OLX scraping page {page_num}: {url}")

                        try:
                            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                            await self._random_delay(2000, 3500)

                            # OLX embeds listing data as __NEXT_DATA__ JSON (Next.js)
                            next_data = await page.evaluate("""
                                () => {
                                    try {
                                        const el = document.getElementById('__NEXT_DATA__');
                                        return el ? JSON.parse(el.textContent) : null;
                                    } catch(e) { return null; }
                                }
                            """)

                            if next_data:
                                page_vehicles = self._parse_next_data(next_data)
                                vehicles.extend(page_vehicles)
                                self.logger.info(f"OLX page {page_num}: extracted {len(page_vehicles)} via __NEXT_DATA__")
                            else:
                                # Fallback: DOM selectors
                                page_vehicles = await self._scrape_dom(page)
                                vehicles.extend(page_vehicles)
                                self.logger.info(f"OLX page {page_num}: extracted {len(page_vehicles)} via DOM")

                        except Exception as e:
                            self.logger.error(f"OLX page {page_num} error: {e}")

                await browser.close()

        except Exception as e:
            self.logger.error(f"OLX scraper fatal error: {e}")

        self.logger.info(f"OLX collected {len(vehicles)} vehicles")
        return vehicles

    async def scrape_stream(self, max_pages: int = 2):
        """Async generator: yields List[dict] per page as they are scraped."""
        from playwright.async_api import async_playwright

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    user_agent=self._get_random_user_agent(),
                    viewport={"width": 1366, "height": 768},
                    locale="pt-BR",
                )
                page = await context.new_page()

                for base_url in self.base_urls:
                    for page_num in range(self.start_page, self.start_page + max_pages):
                        url = self._build_listing_url(page_num, base_url=base_url)
                        self.logger.info(f"OLX stream page {page_num}: {url}")
                        page_vehicles = []
                        try:
                            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                            await self._random_delay(2000, 3500)

                            next_data = await page.evaluate("""
                                () => {
                                    try {
                                        const el = document.getElementById('__NEXT_DATA__');
                                        return el ? JSON.parse(el.textContent) : null;
                                    } catch(e) { return null; }
                                }
                            """)

                            if next_data:
                                page_vehicles = self._parse_next_data(next_data)
                            else:
                                page_vehicles = await self._scrape_dom(page)

                            self.logger.info(f"OLX stream page {page_num}: {len(page_vehicles)} vehicles")
                        except Exception as e:
                            self.logger.error(f"OLX stream page {page_num} error: {e}")

                        yield page_vehicles

                await browser.close()

        except Exception as e:
            self.logger.error(f"OLX stream fatal error: {e}")

    def _parse_next_data(self, data: dict) -> List[dict]:
        results = []
        try:
            # Navigate common Next.js page props structures
            props = data.get("props", {}).get("pageProps", {})
            ads = (
                props.get("ads")
                or props.get("listings")
                or props.get("data", {}).get("ads")
                or props.get("data", {}).get("listings")
                or []
            )
            # Also try initialState / redux store patterns
            if not ads:
                state = props.get("initialState") or props.get("reduxState") or {}
                ads = (
                    state.get("search", {}).get("listings", [])
                    or state.get("ads", {}).get("items", [])
                    or []
                )
            for ad in ads:
                v = self._parse_ad_object(ad)
                if v and v.is_valid():
                    results.append(v.to_dict())
        except Exception as e:
            self.logger.warning(f"OLX __NEXT_DATA__ parse error: {e}")
        return results

    def _parse_ad_object(self, ad: dict) -> Optional[BaseVehicleData]:
        v = BaseVehicleData()
        v.source_name = "OLX"
        try:
            v.titulo = ad.get("subject") or ad.get("title") or ""
            v.titulo = v.titulo.strip()

            # URL
            url = (
                ad.get("friendlyUrl")
                or ad.get("url")
                or ad.get("link")
                or ad.get("source_url")
                or ""
            )
            v.source_url = url if url.startswith("http") else f"https://www.olx.com.br{url}"

            # Price — OLX stores as "R$ 19.000" string in priceValue
            price_raw = (
                ad.get("priceValue")
                or ad.get("price")
                or ""
            )
            if isinstance(price_raw, dict):
                price_raw = price_raw.get("value") or price_raw.get("label") or ""
            v.preco = self._parse_preco(str(price_raw))

            # Location — "Cidade -  UF" or "Cidade, UF"
            location_raw = ad.get("location") or ""
            if location_raw:
                sep = " - " if " - " in location_raw else ("," if "," in location_raw else None)
                if sep:
                    parts = location_raw.split(sep)
                    v.cidade = parts[0].strip()
                    v.estado = parts[-1].strip()[-2:].upper()

            # Photos — list of {"original": url, "originalWebp": url}
            images = ad.get("images") or []
            v.fotos = []
            for img in images:
                if isinstance(img, dict):
                    src = img.get("original") or img.get("originalWebp") or ""
                elif isinstance(img, str):
                    src = img
                else:
                    continue
                if src:
                    v.fotos.append(src)

            # Properties — list of {"name": key, "label": label, "value": val}
            # Real OLX field names:
            #   vehicle_brand, vehicle_model, regdate, mileage, fuel, gearbox
            props = ad.get("properties") or []
            for prop in props:
                if not isinstance(prop, dict):
                    continue
                name = (prop.get("name") or "").lower()
                val = str(prop.get("value") or "").strip()
                if not val:
                    continue

                if name == "vehicle_brand":
                    v.marca = val.title()
                elif name == "vehicle_model":
                    # OLX vehicle_model often is "{Brand} {Model} {Version}" e.g.
                    # "Volkswagen Gol Geração V 1.0 8V..." — strip brand prefix
                    model_val = val.split("/")[0].strip()  # drop version after "/"
                    # Remove brand prefix if present at start
                    brand_lower = (v.marca or "").lower()
                    if brand_lower and model_val.lower().startswith(brand_lower):
                        model_val = model_val[len(brand_lower):].strip()
                    # Take first word (the actual model name)
                    first_word = model_val.split()[0] if model_val.split() else None
                    v.modelo = first_word
                elif name == "regdate":
                    v.ano = self._parse_ano(val)
                elif name == "mileage":
                    v.km = self._parse_km(val)
                elif name == "fuel":
                    v.combustivel = self._normalize_combustivel(val)
                elif name == "gearbox":
                    v.cambio = self._normalize_cambio(val)
                elif name == "seller_type" or name == "owner_type":
                    v.vendedor_tipo = self._normalize_vendedor(val)
                elif name == "car_features":
                    # Store as part of description
                    if val:
                        v.descricao = f"Opcionais: {val}"

            # Seller info
            user = ad.get("user") or {}
            if isinstance(user, dict):
                account_type = user.get("accountType") or ""
                if account_type:
                    v.vendedor_tipo = self._normalize_vendedor(account_type)

            # professionalAd flag
            if ad.get("professionalAd") and not v.vendedor_tipo:
                v.vendedor_tipo = "Loja"
            elif not v.vendedor_tipo:
                v.vendedor_tipo = "Pessoa Física"

            # Post-process: if modelo still equals marca, extract from title
            if v.modelo and v.marca and v.modelo.lower() == v.marca.lower():
                v.modelo = None

            # Try to extract marca/modelo from title if not found in properties
            if not v.marca and v.titulo:
                self._extract_marca_modelo_from_title(v)

            # If we have brand but model came out equal to brand, re-extract from title
            if not v.modelo and v.titulo and v.marca:
                words = v.titulo.split()
                brand_lower = v.marca.lower()
                for i, w in enumerate(words):
                    if w.lower() == brand_lower and i + 1 < len(words):
                        v.modelo = words[i + 1]
                        break

            # Extract year from title as fallback
            if not v.ano and v.titulo:
                v.ano = self._parse_ano(v.titulo)

        except Exception as e:
            self.logger.warning(f"OLX ad parse error: {e}")
        return v

    async def _scrape_dom(self, page) -> List[dict]:
        vehicles = []
        selectors = [
            'li[data-lurker-detail="list_id"]',
            '[data-ds-component="DS-AdCard"]',
            'section[data-testid]',
            '.sc-hmdomO',
        ]
        cards = []
        for sel in selectors:
            cards = await page.query_selector_all(sel)
            if cards:
                break

        for card in cards:
            try:
                v = await self._extract_card_data(card)
                if v and v.is_valid():
                    vehicles.append(v.to_dict())
            except Exception as e:
                self.logger.warning(f"OLX DOM card error: {e}")
        return vehicles

    async def _extract_card_data(self, card, page) -> Optional[BaseVehicleData]:
        v = BaseVehicleData()
        v.source_name = "OLX"

        try:
            link_el = await card.query_selector("a[href*='/autos']")
            if link_el:
                v.source_url = await link_el.get_attribute("href")
                if v.source_url and not v.source_url.startswith("http"):
                    v.source_url = "https://www.olx.com.br" + v.source_url

            title_el = await card.query_selector("h2, h3, [class*='title']")
            if title_el:
                v.titulo = (await title_el.inner_text()).strip()

            price_el = await card.query_selector("[class*='price'], [data-testid*='price']")
            if price_el:
                price_text = await price_el.inner_text()
                v.preco = self._parse_preco(price_text)

            details = await card.query_selector_all("[class*='detail'], [class*='tag']")
            for detail in details:
                text = (await detail.inner_text()).strip().lower()
                if "km" in text:
                    v.km = self._parse_km(text)
                elif re.search(r'\b20[0-2]\d\b|\b19[5-9]\d\b', text):
                    v.ano = self._parse_ano(text)

            location_el = await card.query_selector("[class*='location'], [class*='city']")
            if location_el:
                loc_text = await location_el.inner_text()
                parts = loc_text.split(",")
                if len(parts) >= 2:
                    v.cidade = parts[0].strip()
                    v.estado = parts[-1].strip()[-2:].upper()

            if v.titulo:
                self._extract_marca_modelo_from_title(v)

        except Exception as e:
            self.logger.warning(f"OLX card parse error: {e}")

        return v

    def _extract_marca_modelo_from_title(self, v: BaseVehicleData):
        marcas_conhecidas = [
            "volkswagen", "vw", "chevrolet", "gm", "ford", "fiat", "toyota",
            "honda", "hyundai", "nissan", "renault", "peugeot", "citroën",
            "citroen", "jeep", "mitsubishi", "kia", "bmw", "mercedes", "audi",
            "volvo", "dodge", "ram", "land rover", "jaguar", "lexus", "porsche",
        ]
        title_lower = v.titulo.lower()
        for marca in marcas_conhecidas:
            if marca in title_lower:
                v.marca = marca.title().replace("Vw", "Volkswagen").replace("Gm", "Chevrolet")
                words = v.titulo.split()
                marca_idx = next(
                    (i for i, w in enumerate(words) if w.lower() == marca or w.lower() in marca),
                    -1,
                )
                if marca_idx >= 0 and marca_idx + 1 < len(words):
                    v.modelo = words[marca_idx + 1]
                break
