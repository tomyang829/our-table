import json
import re

import httpx
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_html
from recipe_scrapers._exceptions import (
    NoSchemaFoundInWildMode,
    RecipeSchemaNotFound,
    WebsiteNotImplementedError,
)

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


def _html_fallback(html: str, url: str = "") -> dict:
    """Best-effort metadata extraction for pages without schema.org recipe markup.

    Pulls the page title and og:image so the user can at least save the URL and
    fill in ingredients/instructions manually rather than hitting a hard 422.
    Uses url as last-resort title when the page has no parseable title (e.g. JS-only).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title: og:title > <h1> > <title> > url
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
    if not title and url:
        title = url

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


def _portable_text_to_str(blocks: list) -> str:
    """Concatenate plain text from Sanity Portable Text block list."""
    parts = []
    for block in blocks:
        if block.get("_type") == "block":
            text = "".join(
                span.get("text", "")
                for span in block.get("children", [])
                if span.get("_type") == "span"
            )
            if text.strip():
                parts.append(text.strip())
    return " ".join(parts)


def _extract_madewithlau(html: str) -> dict | None:
    """Extract recipe data from madewithlau.com's __NEXT_DATA__ tRPC state.

    madewithlau.com uses Next.js + Sanity CMS with a custom tRPC API.  The
    recipe is embedded in __NEXT_DATA__ under trpcState.queries[*].state.data
    for the "recipe.bySlug" query key — there is no JSON-LD on the page so
    recipe-scrapers' wild mode finds nothing.
    """
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return None

    try:
        data = json.loads(script.string)
        queries = data["props"]["pageProps"]["trpcState"]["queries"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None

    recipe = None
    for q in queries:
        key = q.get("queryKey", [])
        if key and key[0] == "recipe.bySlug":
            recipe = q.get("state", {}).get("data")
            break

    if not recipe:
        return None

    title = recipe.get("englishTitle") or recipe.get("title")
    description = recipe.get("taglineSummary") or recipe.get("seoDescription")

    image_url = None
    for img_key in ("mainImage", "mainImage16x9"):
        img = recipe.get(img_key)
        if isinstance(img, dict):
            image_url = img.get("asset", {}).get("url")
            if image_url:
                break

    servings = str(recipe["servings"]) if recipe.get("servings") else None

    ingredients = []
    for item in recipe.get("ingredientsArray", []):
        if item.get("_type") != "ingredient":
            continue
        amount = item.get("amount", "")
        unit = item.get("unit", "")
        name = item.get("item", "")
        parts = [str(amount) if amount else "", unit, name]
        ingredient_str = " ".join(p for p in parts if p).strip()
        if ingredient_str:
            ingredients.append(ingredient_str)

    instructions = []
    for step in recipe.get("instructionsArray", []):
        headline = step.get("headline", "")
        desc_text = _portable_text_to_str(step.get("freeformDescription", []))
        if headline and desc_text:
            instructions.append(f"{headline}: {desc_text}")
        elif headline:
            instructions.append(headline)
        elif desc_text:
            instructions.append(desc_text)

    return {
        "title": title,
        "description": description,
        "ingredients": ingredients,
        "instructions": instructions,
        "image_url": image_url,
        "servings": servings,
    }


# Full browser-like headers to avoid 403s from sites that check request headers.
# Use only gzip/deflate so the response is decompressed (httpx doesn't decompress br without brotli).
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _scrape_with_scraper(html: str, url: str):
    """Try site-specific scraper first, then schema.org wild mode. Returns scraper or None."""
    try:
        return scrape_html(html, org_url=url, supported_only=True)
    except WebsiteNotImplementedError:
        try:
            return scrape_html(html, org_url=url, supported_only=False)
        except (NoSchemaFoundInWildMode, RecipeSchemaNotFound):
            return None
    except (NoSchemaFoundInWildMode, RecipeSchemaNotFound):
        return None


async def fetch_and_scrape(url: str) -> dict:
    """Fetch a URL and extract recipe data using recipe-scrapers.

    Tries in order:
    1. Site-specific scrapers (e.g. Half Baked Harvest, 500+ supported sites).
    2. Schema.org Recipe markup (wild mode) for any site with JSON-LD.
    3. Custom extractors for sites with non-standard data embedding
       (e.g. madewithlau.com which uses Next.js + Sanity CMS tRPC state).
    4. Basic HTML metadata (title, description, image) so the user can save the URL
       and fill in ingredients/instructions manually.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url, headers=_BROWSER_HEADERS)
        response.raise_for_status()

    scraper = _scrape_with_scraper(response.text, url)
    if scraper is None:
        mwl = _extract_madewithlau(response.text)
        if mwl is not None:
            return mwl
        return _html_fallback(response.text, url)

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
