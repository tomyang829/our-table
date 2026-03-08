from app.models.user import User


async def test_get_me_returns_current_user(authed_client):
    client, user = authed_client
    response = await client.get("/api/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["email"] == user.email
    assert data["name"] == user.name
    assert data["oauth_provider"] == user.oauth_provider


async def test_get_me_requires_auth(client):
    response = await client.get("/api/users/me")
    assert response.status_code == 401


async def test_update_flavor_profile(authed_client):
    client, _ = authed_client
    flavor = {"spicy": True, "dietary": ["vegetarian"], "dislikes": ["cilantro"]}
    response = await client.put(
        "/api/users/me/flavor-profile",
        json={"flavor_profile": flavor},
    )
    assert response.status_code == 200
    assert response.json()["flavor_profile"] == flavor


async def test_update_flavor_profile_overwrites_previous(authed_client):
    client, _ = authed_client
    await client.put(
        "/api/users/me/flavor-profile",
        json={"flavor_profile": {"first": True}},
    )
    response = await client.put(
        "/api/users/me/flavor-profile",
        json={"flavor_profile": {"second": True}},
    )
    assert response.status_code == 200
    assert response.json()["flavor_profile"] == {"second": True}


async def test_update_flavor_profile_requires_auth(client):
    response = await client.put(
        "/api/users/me/flavor-profile",
        json={"flavor_profile": {"test": True}},
    )
    assert response.status_code == 401


async def test_update_flavor_profile_validates_body(authed_client):
    """Missing flavor_profile key returns 422."""
    client, _ = authed_client
    response = await client.put(
        "/api/users/me/flavor-profile",
        json={"wrong_key": {}},
    )
    assert response.status_code == 422
