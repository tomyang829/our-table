from urllib.parse import parse_qs, urlparse

import httpx
import respx
from jose import jwt as jose_jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token
from app.core.config import settings
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _initiate_login(client, provider: str) -> str:
    """
    Hit the login redirect endpoint to plant the oauth_state cookie in the
    test client's jar, then return the state value (needed as the callback
    query param).
    """
    resp = await client.get(f"/api/auth/{provider}")
    assert resp.status_code == 302
    location = resp.headers["location"]
    return parse_qs(urlparse(location).query)["state"][0]


# ---------------------------------------------------------------------------
# Redirect endpoints
# ---------------------------------------------------------------------------


async def test_google_login_redirects_to_google(client):
    response = await client.get("/api/auth/google")
    assert response.status_code == 302
    location = response.headers["location"]
    assert "accounts.google.com" in location
    assert "response_type=code" in location
    assert "scope=" in location


async def test_google_login_sets_state_cookie(client):
    response = await client.get("/api/auth/google")
    assert "oauth_state" in response.cookies
    state_cookie = response.cookies["oauth_state"]
    # State in the redirect URL must match the cookie
    location = response.headers["location"]
    url_state = parse_qs(urlparse(location).query)["state"][0]
    assert state_cookie == url_state


async def test_github_login_redirects_to_github(client):
    response = await client.get("/api/auth/github")
    assert response.status_code == 302
    location = response.headers["location"]
    assert "github.com/login/oauth/authorize" in location
    assert "scope=" in location


async def test_unknown_provider_callback_returns_400(client):
    response = await client.get("/api/auth/callback/notaprovider?code=x")
    assert response.status_code == 400
    assert "Unknown provider" in response.json()["detail"]


# ---------------------------------------------------------------------------
# State (CSRF) verification
# ---------------------------------------------------------------------------


async def test_callback_rejects_missing_state_param(client):
    response = await client.get("/api/auth/callback/google?code=x")
    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()


async def test_callback_rejects_missing_state_cookie(client):
    """State param present but no cookie → CSRF attempt."""
    response = await client.get(
        "/api/auth/callback/google",
        params={"code": "x", "state": "some_state"},
    )
    assert response.status_code == 400


async def test_callback_rejects_mismatched_state(client):
    await _initiate_login(client, "google")  # plants the real state cookie
    response = await client.get(
        "/api/auth/callback/google",
        params={"code": "x", "state": "tampered_state_value"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Google OAuth callback
# ---------------------------------------------------------------------------


@respx.mock
async def test_google_callback_creates_user_and_sets_jwt_cookie(
    client, db_session: AsyncSession
):
    state = await _initiate_login(client, "google")

    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=httpx.Response(200, json={"access_token": "goog_token_abc"})
    )
    respx.get("https://www.googleapis.com/oauth2/v3/userinfo").mock(
        return_value=httpx.Response(
            200,
            json={
                "sub": "google_sub_create_test",
                "email": "newgoogle@example.com",
                "email_verified": True,
                "name": "Google User",
                "picture": "https://example.com/pic.jpg",
            },
        )
    )

    response = await client.get(
        "/api/auth/callback/google",
        params={"code": "auth_code_123", "state": state},
    )

    assert response.status_code == 302
    assert response.headers["location"] == settings.FRONTEND_URL
    assert "access_token" in response.cookies
    # State cookie must be cleared
    assert response.cookies.get("oauth_state", "") == ""

    # JWT payload must reference the newly created user
    token = response.cookies["access_token"]
    payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    user_id = int(payload["sub"])

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email == "newgoogle@example.com"
    assert user.oauth_provider == "google"
    assert user.oauth_sub == "google_sub_create_test"
    assert user.name == "Google User"
    assert user.avatar_url == "https://example.com/pic.jpg"


@respx.mock
async def test_google_callback_rejects_unverified_email(client):
    state = await _initiate_login(client, "google")

    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=httpx.Response(200, json={"access_token": "goog_token"})
    )
    respx.get("https://www.googleapis.com/oauth2/v3/userinfo").mock(
        return_value=httpx.Response(
            200,
            json={
                "sub": "google_sub_unverified",
                "email": "unverified@example.com",
                "email_verified": False,
                "name": "Unverified User",
            },
        )
    )

    response = await client.get(
        "/api/auth/callback/google",
        params={"code": "code", "state": state},
    )
    assert response.status_code == 400
    assert "verified" in response.json()["detail"].lower()


@respx.mock
async def test_google_callback_updates_existing_user(
    client, db_session: AsyncSession, test_user: User
):
    """Re-logging in with Google updates name/avatar of an existing user."""
    state = await _initiate_login(client, "google")

    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=httpx.Response(200, json={"access_token": "goog_token_update"})
    )
    respx.get("https://www.googleapis.com/oauth2/v3/userinfo").mock(
        return_value=httpx.Response(
            200,
            json={
                "sub": test_user.oauth_sub,
                "email": test_user.email,
                "email_verified": True,
                "name": "Updated Display Name",
                "picture": "https://example.com/new_pic.jpg",
            },
        )
    )

    response = await client.get(
        "/api/auth/callback/google",
        params={"code": "code", "state": state},
    )

    assert response.status_code == 302
    assert "access_token" in response.cookies

    await db_session.refresh(test_user)
    assert test_user.name == "Updated Display Name"
    assert test_user.avatar_url == "https://example.com/new_pic.jpg"


@respx.mock
async def test_google_callback_missing_access_token_returns_400(client):
    state = await _initiate_login(client, "google")

    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=httpx.Response(200, json={"error": "invalid_grant"})
    )

    response = await client.get(
        "/api/auth/callback/google",
        params={"code": "bad_code", "state": state},
    )
    assert response.status_code == 400
    assert "access token" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GitHub OAuth callback
# ---------------------------------------------------------------------------


@respx.mock
async def test_github_callback_creates_user_with_email_in_profile(
    client, db_session: AsyncSession
):
    state = await _initiate_login(client, "github")

    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"access_token": "github_token_xyz"})
    )
    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 77001,
                "login": "ghuser",
                "email": "ghuser@example.com",
                "name": "GitHub User",
                "avatar_url": "https://avatars.githubusercontent.com/u/77001",
            },
        )
    )

    response = await client.get(
        "/api/auth/callback/github",
        params={"code": "github_code", "state": state},
    )

    assert response.status_code == 302
    assert "access_token" in response.cookies

    token = response.cookies["access_token"]
    payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    result = await db_session.execute(
        select(User).where(User.id == int(payload["sub"]))
    )
    user = result.scalar_one()
    assert user.email == "ghuser@example.com"
    assert user.oauth_provider == "github"
    assert user.oauth_sub == "77001"


@respx.mock
async def test_github_callback_fetches_email_when_not_in_profile(
    client, db_session: AsyncSession
):
    """GitHub sometimes returns null email; the callback must fetch /user/emails."""
    state = await _initiate_login(client, "github")

    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"access_token": "github_noemail_token"})
    )
    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 88002,
                "login": "private_email_user",
                "email": None,
                "name": "Private Email User",
                "avatar_url": None,
            },
        )
    )
    respx.get("https://api.github.com/user/emails").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"email": "private@example.com", "primary": True, "verified": True},
                {"email": "other@example.com", "primary": False, "verified": True},
            ],
        )
    )

    response = await client.get(
        "/api/auth/callback/github",
        params={"code": "gh_code_no_email", "state": state},
    )

    assert response.status_code == 302
    assert "access_token" in response.cookies

    result = await db_session.execute(
        select(User).where(User.email == "private@example.com")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.oauth_sub == "88002"


@respx.mock
async def test_github_callback_rejects_when_no_verified_email(client):
    """No verified email from any GitHub source → 400."""
    state = await _initiate_login(client, "github")

    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok"})
    )
    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(
            200,
            json={"id": 99999, "login": "noemail", "email": None, "name": None, "avatar_url": None},
        )
    )
    respx.get("https://api.github.com/user/emails").mock(
        return_value=httpx.Response(200, json=[])
    )

    response = await client.get(
        "/api/auth/callback/github",
        params={"code": "code", "state": state},
    )
    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# JWT middleware — protected route acceptance / rejection
# ---------------------------------------------------------------------------


async def test_protected_route_rejects_missing_token(client):
    response = await client.get("/api/recipes/mine")
    assert response.status_code == 401


async def test_protected_route_rejects_invalid_token(client):
    response = await client.get(
        "/api/recipes/mine",
        cookies={"access_token": "not.a.valid.jwt"},
    )
    assert response.status_code == 401


async def test_protected_route_rejects_token_with_wrong_secret(client):
    from jose import jwt as jose_jwt

    token = jose_jwt.encode({"sub": "1"}, "wrong_secret", algorithm="HS256")
    response = await client.get(
        "/api/recipes/mine",
        cookies={"access_token": token},
    )
    assert response.status_code == 401


async def test_protected_route_accepts_valid_token(client, test_user: User):
    """A real JWT referencing a user in the test DB allows access."""
    token = create_access_token(test_user.id)
    response = await client.get(
        "/api/recipes/mine",
        cookies={"access_token": token},
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_protected_route_rejects_token_for_nonexistent_user(client):
    token = create_access_token(999999)
    response = await client.get(
        "/api/recipes/mine",
        cookies={"access_token": token},
    )
    assert response.status_code == 401
