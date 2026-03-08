import re

import httpx
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_html
from recipe_scrapers._exceptions import NoSchemaFoundInWildMode

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


def _html_fallback(html: str) -> dict:
    """Best-effort metadata extraction for pages without schema.org recipe markup.

    Pulls the page title and og:image so the user can at least save the URL and
    fill in ingredients/instructions manually rather than hitting a hard 422.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title: og:title > <h1> > <title>
    title: str | None = None
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = str(og_title["content"]).strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True) or None
    if not title:
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True) or None

    # Description: og:description > meta description
    description: str | None = None
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        description = str(og_desc["content"]).strip()
    if not description:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = str(meta_desc["content"]).strip()

    # Image: og:image
    image_url: str | None = None
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        image_url = str(og_image["content"]).strip()

    return {
        "title": title,
        "description": description,
        "ingredients": [],
        "instructions": [],
        "image_url": image_url,
        "servings": None,
    }


# Full browser-like headers to avoid 403s from sites that check request headers.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


async def fetch_and_scrape(url: str) -> dict:
    """Fetch a URL and extract recipe data using recipe-scrapers.

    Uses supported_only=False so that any site with schema.org markup is
    attempted via generic parsing, not just the hand-coded site scrapers.

    When no schema markup is found, falls back to basic HTML metadata extraction
    so the user can still save the URL and fill in recipe details manually.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url, headers=_BROWSER_HEADERS)
        response.raise_for_status()

    try:
        scraper = scrape_html(response.text, org_url=url, supported_only=False)
    except NoSchemaFoundInWildMode:
        return _html_fallback(response.text)

    ingredients = _normalise_list(_safe(scraper.ingredients) or [])
    instructions = _normalise_list(_safe(scraper.instructions_list) or [])

    return {
        "title": _safe(scraper.title),
        "description": _safe(scraper.description),
        "ingredients": ingredients,
        "instructions": instructions,
        "image_url": _safe(scraper.image),
        "servings": _safe(scraper.yields),
    }
