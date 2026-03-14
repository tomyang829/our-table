"""Integration tests for /api/recipes/* endpoints."""

import httpx
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source_recipe import SourceRecipe
from app.models.user import User
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
async def test_extract_existing_title_only_source_rescrapes(
    authed_client, db_session: AsyncSession
):
    """If cached source only has fallback metadata, endpoint re-scrapes and updates it."""
    client, _ = authed_client

    existing = SourceRecipe(
        url=RECIPE_URL,
        title="Old Fallback Title",
        ingredients=[],
        instructions=[],
    )
    db_session.add(existing)
    await db_session.flush()

    respx.get(RECIPE_URL).mock(return_value=httpx.Response(200, text=RECIPE_HTML))
    response = await client.post("/api/recipes/extract", json={"url": RECIPE_URL})

    assert response.status_code == 200
    data = response.json()
    assert data["source_recipe"]["id"] == existing.id
    assert data["source_recipe"]["title"] == "Spaghetti Carbonara"
    assert data["source_recipe"]["ingredients"] == [
        "200g spaghetti",
        "100g pancetta",
        "2 eggs",
    ]
    assert len(data["source_recipe"]["instructions"]) == 2
    assert data["partial_parse"] is False


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


# ---------------------------------------------------------------------------
# POST /api/recipes/source/{source_id}/save
# ---------------------------------------------------------------------------


async def test_save_creates_user_recipe(authed_client, db_session: AsyncSession):
    """Saving a source recipe creates a user_recipe copy and returns 201."""
    client, test_user = authed_client

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Original Carbonara",
        ingredients=["200g spaghetti", "100g pancetta"],
        instructions=["Cook pasta.", "Mix eggs."],
    )
    db_session.add(source)
    await db_session.flush()

    response = await client.post(f"/api/recipes/source/{source.id}/save")

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Original Carbonara"
    assert data["user_id"] == test_user.id
    assert data["source_recipe_id"] == source.id
    assert data["ingredients"] == ["200g spaghetti", "100g pancetta"]
    assert data["source_recipe"]["url"] == RECIPE_URL


async def test_save_with_notes(authed_client, db_session: AsyncSession):
    """Optional notes are stored on the user_recipe."""
    client, _ = authed_client

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Carbonara",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(source)
    await db_session.flush()

    response = await client.post(
        f"/api/recipes/source/{source.id}/save",
        json={"notes": "Add more pepper"},
    )

    assert response.status_code == 201
    assert response.json()["notes"] == "Add more pepper"


async def test_save_nonexistent_source_returns_404(authed_client):
    """Trying to save a source_recipe that does not exist returns 404."""
    client, _ = authed_client

    response = await client.post("/api/recipes/source/99999/save")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_save_requires_auth(client):
    """Unauthenticated save requests are rejected with 401."""
    response = await client.post("/api/recipes/source/1/save")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/recipes/mine
# ---------------------------------------------------------------------------


async def test_create_recipe_from_scratch(authed_client):
    """Creating a recipe from scratch stores both source and user copies."""
    client, test_user = authed_client

    response = await client.post(
        "/api/recipes/mine",
        json={
            "title": "Grandma's Soup",
            "ingredients": ["2 carrots", "1 onion"],
            "instructions": ["Chop vegetables", "Simmer 30 minutes"],
            "notes": "Best with crusty bread",
            "servings": "4",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == test_user.id
    assert data["title"] == "Grandma's Soup"
    assert data["ingredients"] == ["2 carrots", "1 onion"]
    assert data["instructions"] == ["Chop vegetables", "Simmer 30 minutes"]
    assert data["notes"] == "Best with crusty bread"
    assert data["servings"] == "4"
    assert data["source_recipe"]["url"].startswith(f"manual://{test_user.id}/")


async def test_create_recipe_trims_whitespace(authed_client):
    """Whitespace-only list entries are removed and strings are trimmed."""
    client, _ = authed_client

    response = await client.post(
        "/api/recipes/mine",
        json={
            "title": "  Quick Salad  ",
            "ingredients": [" lettuce ", "   ", ""],
            "instructions": [" rinse ", "  ", "serve"],
            "notes": "  use olive oil ",
            "servings": " 2 bowls ",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Quick Salad"
    assert data["ingredients"] == ["lettuce"]
    assert data["instructions"] == ["rinse", "serve"]
    assert data["notes"] == "use olive oil"
    assert data["servings"] == "2 bowls"


async def test_create_recipe_requires_title(authed_client):
    """Creating a manual recipe without title returns 422."""
    client, _ = authed_client

    response = await client.post(
        "/api/recipes/mine",
        json={"title": "   ", "ingredients": [], "instructions": []},
    )

    assert response.status_code == 422


async def test_create_recipe_requires_auth(client):
    """Unauthenticated create requests are rejected with 401."""
    response = await client.post(
        "/api/recipes/mine",
        json={"title": "No Auth Recipe", "ingredients": [], "instructions": []},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/recipes/mine
# ---------------------------------------------------------------------------


async def test_list_returns_users_recipes(authed_client, db_session: AsyncSession):
    """GET /mine returns only the current user's saved recipes."""
    client, test_user = authed_client

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Carbonara",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(source)
    await db_session.flush()

    recipe1 = UserRecipe(
        user_id=test_user.id,
        source_recipe_id=source.id,
        title="My Carbonara",
    )
    recipe2 = UserRecipe(
        user_id=test_user.id,
        source_recipe_id=source.id,
        title="My Second Carbonara",
    )
    db_session.add_all([recipe1, recipe2])
    await db_session.flush()

    response = await client.get("/api/recipes/mine")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = {r["title"] for r in data}
    assert titles == {"My Carbonara", "My Second Carbonara"}


async def test_list_excludes_other_users_recipes(authed_client, db_session: AsyncSession):
    """Recipes belonging to another user are not returned."""
    client, test_user = authed_client

    other_user = User(
        email="other@example.com",
        name="Other User",
        oauth_provider="google",
        oauth_sub="google_sub_other_456",
    )
    db_session.add(other_user)

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Carbonara",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(source)
    await db_session.flush()

    own = UserRecipe(user_id=test_user.id, source_recipe_id=source.id, title="Mine")
    others = UserRecipe(user_id=other_user.id, source_recipe_id=source.id, title="Theirs")
    db_session.add_all([own, others])
    await db_session.flush()

    response = await client.get("/api/recipes/mine")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Mine"


async def test_list_empty_returns_empty_array(authed_client):
    """When the user has no recipes, an empty list is returned."""
    client, _ = authed_client

    response = await client.get("/api/recipes/mine")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_requires_auth(client):
    """Unauthenticated list requests are rejected with 401."""
    response = await client.get("/api/recipes/mine")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/recipes/mine/{id}
# ---------------------------------------------------------------------------


async def test_get_detail_returns_recipe_with_source(authed_client, db_session: AsyncSession):
    """GET /mine/{id} returns the user recipe along with the original source_recipe."""
    client, test_user = authed_client

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Original Carbonara",
        ingredients=["200g spaghetti"],
        instructions=["Cook pasta."],
    )
    db_session.add(source)
    await db_session.flush()

    recipe = UserRecipe(
        user_id=test_user.id,
        source_recipe_id=source.id,
        title="My Carbonara",
        notes="Less salt",
    )
    db_session.add(recipe)
    await db_session.flush()

    response = await client.get(f"/api/recipes/mine/{recipe.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == recipe.id
    assert data["title"] == "My Carbonara"
    assert data["notes"] == "Less salt"
    assert data["source_recipe"] is not None
    assert data["source_recipe"]["url"] == RECIPE_URL
    assert data["source_recipe"]["title"] == "Original Carbonara"


async def test_get_detail_not_found_returns_404(authed_client):
    """Requesting a recipe that does not exist returns 404."""
    client, _ = authed_client

    response = await client.get("/api/recipes/mine/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_get_detail_other_users_recipe_returns_404(authed_client, db_session: AsyncSession):
    """A user cannot access another user's recipe — 404 (not 403) to avoid enumeration."""
    client, _ = authed_client

    other_user = User(
        email="other@example.com",
        name="Other User",
        oauth_provider="github",
        oauth_sub="github_sub_789",
    )
    db_session.add(other_user)

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Carbonara",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(source)
    await db_session.flush()

    other_recipe = UserRecipe(
        user_id=other_user.id,
        source_recipe_id=source.id,
        title="Their Recipe",
    )
    db_session.add(other_recipe)
    await db_session.flush()

    response = await client.get(f"/api/recipes/mine/{other_recipe.id}")

    assert response.status_code == 404


async def test_get_detail_requires_auth(client):
    """Unauthenticated detail requests are rejected with 401."""
    response = await client.get("/api/recipes/mine/1")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/recipes/mine/{id}
# ---------------------------------------------------------------------------


async def test_update_patches_fields(authed_client, db_session: AsyncSession):
    """PUT /mine/{id} updates only the fields provided in the body."""
    client, test_user = authed_client

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Carbonara",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(source)
    await db_session.flush()

    recipe = UserRecipe(
        user_id=test_user.id,
        source_recipe_id=source.id,
        title="Original Title",
        ingredients=["pasta"],
        instructions=["cook"],
        notes=None,
    )
    db_session.add(recipe)
    await db_session.flush()

    response = await client.put(
        f"/api/recipes/mine/{recipe.id}",
        json={"title": "Updated Title", "notes": "My note"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["notes"] == "My note"
    assert data["ingredients"] == ["pasta"]


async def test_update_all_editable_fields(authed_client, db_session: AsyncSession):
    """All four editable fields can be updated in one request."""
    client, test_user = authed_client

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Carbonara",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(source)
    await db_session.flush()

    recipe = UserRecipe(
        user_id=test_user.id,
        source_recipe_id=source.id,
        title="Old Title",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(recipe)
    await db_session.flush()

    response = await client.put(
        f"/api/recipes/mine/{recipe.id}",
        json={
            "title": "New Title",
            "ingredients": ["egg", "bacon"],
            "instructions": ["step 1", "step 2"],
            "notes": "Serve hot",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["ingredients"] == ["egg", "bacon"]
    assert data["instructions"] == ["step 1", "step 2"]
    assert data["notes"] == "Serve hot"


async def test_update_not_found_returns_404(authed_client):
    """Updating a non-existent recipe returns 404."""
    client, _ = authed_client

    response = await client.put(
        "/api/recipes/mine/99999",
        json={"title": "Ghost Recipe"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_update_other_users_recipe_returns_404(authed_client, db_session: AsyncSession):
    """A user cannot update another user's recipe."""
    client, _ = authed_client

    other_user = User(
        email="other@example.com",
        name="Other User",
        oauth_provider="github",
        oauth_sub="github_sub_update_test",
    )
    db_session.add(other_user)

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Carbonara",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(source)
    await db_session.flush()

    other_recipe = UserRecipe(
        user_id=other_user.id,
        source_recipe_id=source.id,
        title="Their Recipe",
    )
    db_session.add(other_recipe)
    await db_session.flush()

    response = await client.put(
        f"/api/recipes/mine/{other_recipe.id}",
        json={"title": "Hijacked"},
    )

    assert response.status_code == 404


async def test_update_requires_auth(client):
    """Unauthenticated update requests are rejected with 401."""
    response = await client.put("/api/recipes/mine/1", json={"title": "X"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/recipes/mine/{id}
# ---------------------------------------------------------------------------


async def test_delete_removes_recipe(authed_client, db_session: AsyncSession):
    """DELETE /mine/{id} removes the recipe and returns 204."""
    client, test_user = authed_client

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Carbonara",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(source)
    await db_session.flush()

    recipe = UserRecipe(
        user_id=test_user.id,
        source_recipe_id=source.id,
        title="To Delete",
    )
    db_session.add(recipe)
    await db_session.flush()
    recipe_id = recipe.id

    response = await client.delete(f"/api/recipes/mine/{recipe_id}")

    assert response.status_code == 204

    # Confirm it's gone from the DB
    check = await db_session.get(UserRecipe, recipe_id)
    assert check is None


async def test_delete_not_found_returns_404(authed_client):
    """Deleting a non-existent recipe returns 404."""
    client, _ = authed_client

    response = await client.delete("/api/recipes/mine/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_delete_other_users_recipe_returns_404(
    authed_client, db_session: AsyncSession
):
    """A user cannot delete another user's recipe — 404 to avoid enumeration."""
    client, _ = authed_client

    other_user = User(
        email="other@example.com",
        name="Other User",
        oauth_provider="github",
        oauth_sub="github_sub_delete_test",
    )
    db_session.add(other_user)

    source = SourceRecipe(
        url=RECIPE_URL,
        title="Carbonara",
        ingredients=["pasta"],
        instructions=["cook"],
    )
    db_session.add(source)
    await db_session.flush()

    other_recipe = UserRecipe(
        user_id=other_user.id,
        source_recipe_id=source.id,
        title="Their Recipe",
    )
    db_session.add(other_recipe)
    await db_session.flush()

    response = await client.delete(f"/api/recipes/mine/{other_recipe.id}")

    assert response.status_code == 404


async def test_delete_requires_auth(client):
    """Unauthenticated delete requests are rejected with 401."""
    response = await client.delete("/api/recipes/mine/1")
    assert response.status_code == 401
