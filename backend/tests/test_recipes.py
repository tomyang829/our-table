"""Integration tests for /api/recipes/* endpoints."""

import httpx
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source_recipe import SourceRecipe
from app.models.user_recipe import UserRecipe

RECIPE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <script type="application/ld+json">
  {
    "@context": "http://schema.org",
    "@type": "Recipe",
    "name": "Spaghetti Carbonara",
    "description": "Classic Italian pasta",
    "recipeIngredient": ["200g spaghetti", "100g pancetta", "2 eggs"],
    "recipeInstructions": [
      {"@type": "HowToStep", "text": "Cook spaghetti."},
      {"@type": "HowToStep", "text": "Mix eggs and pancetta."}
    ],
    "image": "https://example.com/carbonara.jpg"
  }
  </script>
</head>
<body><h1>Spaghetti Carbonara</h1></body>
</html>
"""

RECIPE_URL = "https://example.com/recipes/carbonara"


@respx.mock
async def test_extract_new_url_scrapes_and_creates_source(authed_client):
    """A brand-new URL is scraped and a source_recipe record is created."""
    client, _ = authed_client
    respx.get(RECIPE_URL).mock(return_value=httpx.Response(200, text=RECIPE_HTML))

    response = await client.post("/api/recipes/extract", json={"url": RECIPE_URL})

    assert response.status_code == 200
    data = response.json()
    assert data["source_recipe"]["title"] == "Spaghetti Carbonara"
    assert data["source_recipe"]["url"] == RECIPE_URL
    assert data["source_recipe"]["id"] is not None
    assert "200g spaghetti" in data["source_recipe"]["ingredients"]
    assert len(data["source_recipe"]["instructions"]) == 2


@respx.mock
async def test_extract_existing_source_returns_without_scraping(
    authed_client, db_session: AsyncSession
):
    """If the URL is already in source_recipes, return it without hitting the network."""
    client, _ = authed_client

    existing = SourceRecipe(
        url=RECIPE_URL,
        title="Cached Carbonara",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(existing)
    await db_session.flush()

    # No respx mock registered — if a real HTTP call is made the test would fail
    response = await client.post("/api/recipes/extract", json={"url": RECIPE_URL})

    assert response.status_code == 200
    data = response.json()
    assert data["source_recipe"]["title"] == "Cached Carbonara"
    assert data["source_recipe"]["id"] == existing.id


@respx.mock
async def test_extract_duplicate_user_save_returns_409(
    authed_client, db_session: AsyncSession
):
    """If the user already saved a recipe from this URL, return 409."""
    client, test_user = authed_client

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Carbonara",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(source)
    await db_session.flush()

    user_recipe = UserRecipe(
        user_id=test_user.id,
        source_recipe_id=source.id,
        title="My Carbonara",
    )
    db_session.add(user_recipe)
    await db_session.flush()

    response = await client.post("/api/recipes/extract", json={"url": RECIPE_URL})

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["existing_recipe_id"] == user_recipe.id
    assert "already saved" in detail["message"]


async def test_extract_requires_auth(client):
    """Unauthenticated requests to /extract are rejected with 401."""
    response = await client.post(
        "/api/recipes/extract", json={"url": RECIPE_URL}
    )
    assert response.status_code == 401


@respx.mock
async def test_extract_bad_url_returns_422(authed_client):
    """A URL that returns an HTTP error surfaces as 422."""
    client, _ = authed_client
    bad_url = "https://example.com/not-found"
    respx.get(bad_url).mock(return_value=httpx.Response(404))

    response = await client.post("/api/recipes/extract", json={"url": bad_url})

    assert response.status_code == 422
    assert "Failed to fetch URL" in response.json()["detail"]
