import re

import httpx
from recipe_scrapers import scrape_html

# Matches the start of a numbered step like "1. " or "1) " that is NOT preceded
# by another digit (to avoid splitting "3.5 cups" or "step 1.2").
_NUMBERED_STEP = re.compile(r'(?<!\d)(?=\d+[.)]\s)')


def _safe(fn):
    try:
        result = fn()
        return result if result else None
    except Exception:
        return None


def _normalise_list(items: list[str]) -> list[str]:
    """Ensure every element in an instructions/ingredients list is a single step.

    recipe-scrapers can return items that bundle multiple steps together as:
      - Newline-separated text  ("Step 1.\\nStep 2.")
      - Inline-numbered text    ("1. Step one. 2. Step two.")

    This function splits both forms and strips surrounding whitespace so the DB
    always stores one step per array element.
    """
    result = []
    for item in items:
        for line in item.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in _NUMBERED_STEP.split(line) if p.strip()]
            result.extend(parts if len(parts) > 1 else [line])
    return result


async def fetch_and_scrape(url: str) -> dict:
    """Fetch a URL and extract recipe data using recipe-scrapers.

    Uses supported_only=False so that any site with schema.org markup is
    attempted via generic parsing, not just the hand-coded site scrapers.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

    scraper = scrape_html(response.text, org_url=url, supported_only=False)

    ingredients = _normalise_list(_safe(scraper.ingredients) or [])
    instructions = _normalise_list(_safe(scraper.instructions_list) or [])

    return {
        "title": _safe(scraper.title),
        "description": _safe(scraper.description),
        "ingredients": ingredients,
        "instructions": instructions,
        "image_url": _safe(scraper.image),
    }
