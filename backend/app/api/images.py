from fastapi import APIRouter, HTTPException, Response
from urllib.parse import urlparse, unquote
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

# Only proxy images from trusted car-listing domains
ALLOWED_HOSTS = {
    "img.olx.com.br",
    "img1.olxcdn.com",
    "img2.olxcdn.com",
    "img.olxcdn.com",
    "olxbr-prod.akamaized.net",
    "static.olx.com.br",
    "cdn.olx.com.br",
    "img.webmotors.com.br",
    "iwcdn.webmotors.com.br",
    "static.webmotors.com.br",
    "fotos.icarros.com.br",
    "img.icarros.com.br",
    "img0.icarros.com",
    "img1.icarros.com",
    "img2.icarros.com",
    "img3.icarros.com",
    "static.icarros.com.br",
    "cdn.napista.com.br",
    "static.napista.com.br",
    "images.napista.com.br",
    "i.mlcdn.com.br",
    "http2.mlstatic.com",
}

# Referer to use per domain keyword
REFERER_MAP = {
    "olx": "https://www.olx.com.br/",
    "webmotors": "https://www.webmotors.com.br/",
    "icarros": "https://www.icarros.com.br/",
    "napista": "https://www.napista.com.br/",
    "mlstatic": "https://www.mercadolivre.com.br/",
    "mlcdn": "https://www.mercadolivre.com.br/",
}


def _get_referer(hostname: str) -> str:
    for key, ref in REFERER_MAP.items():
        if key in hostname:
            return ref
    return "https://www.google.com/"


@router.get("/proxy")
async def proxy_image(url: str):
    """Proxy a car-listing image with the correct Referer header to bypass hotlink protection."""
    decoded = unquote(url)
    try:
        parsed = urlparse(decoded)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")

    hostname = parsed.hostname or ""

    # Wildcard match: allow known CDN subdomains (*.olxcdn.com, *.webmotors.com.br, etc.)
    allowed = hostname in ALLOWED_HOSTS or any(
        hostname.endswith("." + h.lstrip("*.")) or hostname == h.lstrip("*.")
        for h in {
            "*.olxcdn.com", "*.olx.com.br", "*.webmotors.com.br",
            "*.icarros.com.br", "*.icarros.com", "*.napista.com.br",
            "*.cloudfront.net", "*.akamaized.net", "*.mlstatic.com",
            "*.mlcdn.com.br", "*.amazonaws.com",
        }
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Domain not allowed")

    referer = _get_referer(hostname)

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": referer,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            },
        ) as client:
            resp = await client.get(decoded)
    except httpx.RequestError as e:
        logger.warning("Image proxy fetch error for %s: %s", decoded, e)
        raise HTTPException(status_code=502, detail="Could not fetch image")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Upstream error")

    content_type = resp.headers.get("content-type", "image/jpeg")
    return Response(
        content=resp.content,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Proxied-From": hostname,
        },
    )
