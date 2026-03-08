import httpx
from recipe_scrapers import scrape_html


def _safe(fn):
    try:
        result = fn()
        return result if result else None
    except Exception:
        return None


async def fetch_and_scrape(url: str) -> dict:
    """Fetch a URL and extract recipe data using recipe-scrapers.

    Uses supported_only=False so that any site with schema.org markup is
    attempted via generic parsing, not just the hand-coded site scrapers.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

    scraper = scrape_html(response.text, org_url=url, supported_only=False)

    ingredients = _safe(scraper.ingredients) or []
    instructions = _safe(scraper.instructions_list) or []

    return {
        "title": _safe(scraper.title),
        "description": _safe(scraper.description),
        "ingredients": ingredients,
        "instructions": instructions,
        "image_url": _safe(scraper.image),
    }
