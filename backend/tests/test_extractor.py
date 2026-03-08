"""Unit tests for the recipe extraction service."""

import httpx
import pytest
import respx

from app.services.extractor import fetch_and_scrape

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
