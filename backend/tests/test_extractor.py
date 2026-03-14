"""Unit tests for the recipe extraction service."""

import json

import httpx
import pytest
import respx

from app.services.extractor import _extract_madewithlau, _portable_text_to_str, fetch_and_scrape

RECIPE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <script type="application/ld+json">
  {
    "@context": "http://schema.org",
    "@type": "Recipe",
    "name": "Test Pasta",
    "description": "A simple pasta dish",
    "recipeIngredient": ["200g pasta", "2 cloves garlic", "olive oil"],
    "recipeInstructions": [
      {"@type": "HowToStep", "text": "Boil pasta."},
      {"@type": "HowToStep", "text": "Fry garlic in oil."}
    ],
    "image": "https://example.com/pasta.jpg"
  }
  </script>
</head>
<body><h1>Test Pasta</h1></body>
</html>
"""

TEST_URL = "https://example.com/recipes/pasta"


@respx.mock
async def test_fetch_and_scrape_returns_recipe_data():
    respx.get(TEST_URL).mock(return_value=httpx.Response(200, text=RECIPE_HTML))

    result = await fetch_and_scrape(TEST_URL)

    assert result["title"] == "Test Pasta"
    assert result["description"] == "A simple pasta dish"
    assert "200g pasta" in result["ingredients"]
    assert len(result["instructions"]) == 2
    assert result["image_url"] == "https://example.com/pasta.jpg"


@respx.mock
async def test_fetch_and_scrape_raises_on_http_error():
    respx.get(TEST_URL).mock(return_value=httpx.Response(404))

    with pytest.raises(httpx.HTTPStatusError):
        await fetch_and_scrape(TEST_URL)


@respx.mock
async def test_fetch_and_scrape_splits_newline_embedded_instructions():
    """Plain-text recipeInstructions with embedded newlines are split into steps."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <script type="application/ld+json">
      {
        "@context": "http://schema.org",
        "@type": "Recipe",
        "name": "Newline Recipe",
        "recipeIngredient": ["1 egg"],
        "recipeInstructions": "Step one.\nStep two.\nStep three."
      }
      </script>
    </head>
    <body></body>
    </html>
    """
    respx.get(TEST_URL).mock(return_value=httpx.Response(200, text=html))

    result = await fetch_and_scrape(TEST_URL)

    assert result["instructions"] == ["Step one.", "Step two.", "Step three."]


@respx.mock
async def test_fetch_and_scrape_splits_numbered_inline_instructions():
    """Inline-numbered instructions ('1. Step. 2. Step.') are split into steps."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <script type="application/ld+json">
      {
        "@context": "http://schema.org",
        "@type": "Recipe",
        "name": "Numbered Recipe",
        "recipeIngredient": ["1 egg"],
        "recipeInstructions": "1. Cook the pasta. 2. Fry the garlic. 3. Combine and serve."
      }
      </script>
    </head>
    <body></body>
    </html>
    """
    respx.get(TEST_URL).mock(return_value=httpx.Response(200, text=html))

    result = await fetch_and_scrape(TEST_URL)

    assert result["instructions"] == [
        "1. Cook the pasta.",
        "2. Fry the garlic.",
        "3. Combine and serve.",
    ]


@respx.mock
async def test_fetch_and_scrape_fallback_when_no_recipe_schema():
    """When the page has no schema.org Recipe (e.g. Sally's Baking Addiction), use HTML fallback."""
    html_no_schema = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta property="og:title" content="Rosemary Garlic Pull Apart Bread" />
      <meta property="og:description" content="Flaky and flavorful pull apart bread." />
      <meta property="og:image" content="https://example.com/bread.jpg" />
    </head>
    <body><h1>Rosemary Garlic Pull Apart Bread</h1></body>
    </html>
    """
    respx.get(TEST_URL).mock(return_value=httpx.Response(200, text=html_no_schema))

    # recipe-scrapers raises RecipeSchemaNotFound when no Recipe schema is present
    result = await fetch_and_scrape(TEST_URL)

    assert result["title"] == "Rosemary Garlic Pull Apart Bread"
    assert result["description"] == "Flaky and flavorful pull apart bread."
    assert result["image_url"] == "https://example.com/bread.jpg"
    assert result["ingredients"] == []
    assert result["instructions"] == []


@respx.mock
async def test_fetch_and_scrape_fallback_uses_url_when_no_meta():
    """When the page has no parseable title (e.g. JS-only), use URL as title."""
    html_js_only = "<!DOCTYPE html><html><body><div id='root'></div></body></html>"
    respx.get(TEST_URL).mock(return_value=httpx.Response(200, text=html_js_only))

    result = await fetch_and_scrape(TEST_URL)

    assert result["title"] == TEST_URL
    assert result["ingredients"] == []
    assert result["instructions"] == []


@respx.mock
async def test_fetch_and_scrape_handles_missing_optional_fields():
    minimal_html = """
    <!DOCTYPE html>
    <html>
    <head>
      <script type="application/ld+json">
      {
        "@context": "http://schema.org",
        "@type": "Recipe",
        "name": "Minimal Recipe",
        "recipeIngredient": ["1 egg"],
        "recipeInstructions": [{"@type": "HowToStep", "text": "Cook egg."}]
      }
      </script>
    </head>
    <body></body>
    </html>
    """
    respx.get(TEST_URL).mock(return_value=httpx.Response(200, text=minimal_html))

    result = await fetch_and_scrape(TEST_URL)

    assert result["title"] == "Minimal Recipe"
    assert result["ingredients"] == ["1 egg"]
    assert result["instructions"] == ["Cook egg."]
    # Optional fields should be None or absent, not raise
    assert "image_url" in result
    assert "description" in result


# ---------------------------------------------------------------------------
# madewithlau.com — Next.js + Sanity CMS tRPC extraction
# ---------------------------------------------------------------------------

MWL_NEXT_DATA = {
    "props": {
        "pageProps": {
            "trpcState": {
                "mutations": [],
                "queries": [
                    {
                        "queryKey": ["recipe.bySlug", {"slug": "clay-pot-rice"}],
                        "state": {
                            "data": {
                                "englishTitle": "Clay Pot Rice",
                                "taglineSummary": "A comforting Cantonese classic.",
                                "servings": 4,
                                "mainImage": {
                                    "asset": {
                                        "url": "https://cdn.sanity.io/images/test/claypot.jpg"
                                    }
                                },
                                "ingredientsArray": [
                                    {
                                        "_type": "ingredientSection",
                                        "section": "Main Ingredients",
                                    },
                                    {
                                        "_type": "ingredient",
                                        "amount": 10,
                                        "unit": "oz",
                                        "item": "long grain rice",
                                    },
                                    {
                                        "_type": "ingredient",
                                        "amount": 2,
                                        "item": "Chinese sausage",
                                    },
                                ],
                                "instructionsArray": [
                                    {
                                        "headline": "Prepare rice",
                                        "freeformDescription": [
                                            {
                                                "_type": "block",
                                                "children": [
                                                    {
                                                        "_type": "span",
                                                        "text": "Wash the rice three times.",
                                                    }
                                                ],
                                            }
                                        ],
                                    },
                                    {
                                        "headline": "Cook in clay pot",
                                        "freeformDescription": [
                                            {
                                                "_type": "block",
                                                "children": [
                                                    {
                                                        "_type": "span",
                                                        "text": "Add rice and water to pot.",
                                                    },
                                                ],
                                            },
                                            {
                                                "_type": "block",
                                                "children": [
                                                    {
                                                        "_type": "span",
                                                        "text": "Cook on medium heat.",
                                                    }
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            }
                        },
                    }
                ],
            }
        }
    },
    "page": "/recipes/[post]",
    "query": {"post": "clay-pot-rice"},
    "buildId": "abc123",
    "isFallback": False,
    "gsp": True,
}

MWL_URL = "https://www.madewithlau.com/recipes/clay-pot-rice"


def _make_mwl_html(next_data: dict) -> str:
    payload = json.dumps(next_data)
    return f"""<!DOCTYPE html>
<html><head>
<title>Clay Pot Rice</title>
<script id="__NEXT_DATA__" type="application/json">{payload}</script>
</head><body></body></html>"""


def test_portable_text_to_str_concatenates_spans():
    blocks = [
        {
            "_type": "block",
            "children": [
                {"_type": "span", "text": "Hello "},
                {"_type": "span", "text": "world"},
            ],
        },
        {
            "_type": "block",
            "children": [{"_type": "span", "text": "Second paragraph."}],
        },
    ]
    assert _portable_text_to_str(blocks) == "Hello world Second paragraph."


def test_portable_text_to_str_ignores_non_block_types():
    blocks = [
        {"_type": "image", "asset": {}},
        {"_type": "block", "children": [{"_type": "span", "text": "Only this."}]},
    ]
    assert _portable_text_to_str(blocks) == "Only this."


def test_extract_madewithlau_title_and_description():
    html = _make_mwl_html(MWL_NEXT_DATA)
    result = _extract_madewithlau(html)

    assert result is not None
    assert result["title"] == "Clay Pot Rice"
    assert result["description"] == "A comforting Cantonese classic."


def test_extract_madewithlau_ingredients():
    html = _make_mwl_html(MWL_NEXT_DATA)
    result = _extract_madewithlau(html)

    assert result is not None
    assert "10 oz long grain rice" in result["ingredients"]
    # Ingredient with no unit
    assert "2 Chinese sausage" in result["ingredients"]
    # Section headers are skipped
    assert len(result["ingredients"]) == 2


def test_extract_madewithlau_instructions():
    html = _make_mwl_html(MWL_NEXT_DATA)
    result = _extract_madewithlau(html)

    assert result is not None
    assert len(result["instructions"]) == 2
    assert result["instructions"][0] == "Prepare rice: Wash the rice three times."
    assert result["instructions"][1] == "Cook in clay pot: Add rice and water to pot. Cook on medium heat."


def test_extract_madewithlau_image_and_servings():
    html = _make_mwl_html(MWL_NEXT_DATA)
    result = _extract_madewithlau(html)

    assert result is not None
    assert result["image_url"] == "https://cdn.sanity.io/images/test/claypot.jpg"
    assert result["servings"] == "4"


def test_extract_madewithlau_returns_none_without_next_data():
    html = "<html><body>No __NEXT_DATA__ here.</body></html>"
    assert _extract_madewithlau(html) is None


def test_extract_madewithlau_returns_none_when_no_recipe_query():
    data = {
        "props": {
            "pageProps": {
                "trpcState": {
                    "queries": [
                        {
                            "queryKey": ["recipe.latest", {"numberOfRecipes": 5}],
                            "state": {"data": []},
                        }
                    ]
                }
            }
        },
        "page": "/",
        "query": {},
        "buildId": "abc",
        "isFallback": False,
        "gsp": True,
    }
    assert _extract_madewithlau(_make_mwl_html(data)) is None


@respx.mock
async def test_fetch_and_scrape_uses_madewithlau_extractor():
    """fetch_and_scrape picks up madewithlau.com's tRPC-embedded recipe data."""
    respx.get(MWL_URL).mock(
        return_value=httpx.Response(200, text=_make_mwl_html(MWL_NEXT_DATA))
    )

    result = await fetch_and_scrape(MWL_URL)

    assert result["title"] == "Clay Pot Rice"
    assert len(result["ingredients"]) == 2
    assert len(result["instructions"]) == 2
    assert result["image_url"] == "https://cdn.sanity.io/images/test/claypot.jpg"
