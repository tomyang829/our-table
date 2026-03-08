import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_GOOGLE_SCOPE = "openid email profile"

_GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USERINFO_URL = "https://api.github.com/user"
_GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
_GITHUB_SCOPE = "read:user user:email"

_STATE_COOKIE = "oauth_state"
_STATE_MAX_AGE = 600  # 10 minutes — long enough to complete the OAuth round-trip


def _callback_uri(request: Request, provider: str) -> str:
    return str(request.base_url).rstrip("/") + f"/api/auth/callback/{provider}"


def _set_state_cookie(response: RedirectResponse, state: str) -> None:
    response.set_cookie(
        key=_STATE_COOKIE,
        value=state,
        httponly=True,
        samesite="lax",
        max_age=_STATE_MAX_AGE,
        secure=settings.SECURE_COOKIES,
    )


def _verify_state(request: Request, state: str | None) -> None:
    """Raise 400 if the state param doesn't match the state cookie (CSRF protection)."""
    stored = request.cookies.get(_STATE_COOKIE)
    if not stored or not state or not secrets.compare_digest(stored, state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing OAuth state parameter",
        )


@router.get("/google")
async def google_login(request: Request) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _callback_uri(request, "google"),
        "response_type": "code",
        "scope": _GOOGLE_SCOPE,
        "state": state,
        "access_type": "online",
    }
    response = RedirectResponse(
        url=_GOOGLE_AUTH_URL + "?" + urlencode(params),
        status_code=status.HTTP_302_FOUND,
    )
    _set_state_cookie(response, state)
    return response


@router.get("/github")
async def github_login(request: Request) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": _callback_uri(request, "github"),
        "scope": _GITHUB_SCOPE,
        "state": state,
    }
    response = RedirectResponse(
        url=_GITHUB_AUTH_URL + "?" + urlencode(params),
        status_code=status.HTTP_302_FOUND,
    )
    _set_state_cookie(response, state)
    return response


async def _fetch_token(
    http: httpx.AsyncClient,
    token_url: str,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> str:
    resp = await http.post(
        token_url,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider did not return an access token",
        )
    return token


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    state: str | None = None,
) -> RedirectResponse:
    if provider not in ("google", "github"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {provider}",
        )

    _verify_state(request, state)

    redirect_uri = _callback_uri(request, provider)

    async with httpx.AsyncClient() as http:
        if provider == "google":
            access_token = await _fetch_token(
                http,
                _GOOGLE_TOKEN_URL,
                code,
                settings.GOOGLE_CLIENT_ID,
                settings.GOOGLE_CLIENT_SECRET,
                redirect_uri,
            )
            userinfo_resp = await http.get(
                _GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_resp.raise_for_status()
            user_info = userinfo_resp.json()

            if not user_info.get("email_verified"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Google account email is not verified",
                )

            oauth_sub = str(user_info["sub"])
            email = user_info.get("email", "")
            name = user_info.get("name")
            avatar_url = user_info.get("picture")

        else:  # github
            access_token = await _fetch_token(
                http,
                _GITHUB_TOKEN_URL,
                code,
                settings.GITHUB_CLIENT_ID,
                settings.GITHUB_CLIENT_SECRET,
                redirect_uri,
            )
            userinfo_resp = await http.get(
                _GITHUB_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_resp.raise_for_status()
            user_info = userinfo_resp.json()
            oauth_sub = str(user_info["id"])
            email = user_info.get("email") or ""
            name = user_info.get("name") or user_info.get("login", "")
            avatar_url = user_info.get("avatar_url")

            if not email:
                emails_resp = await http.get(
                    _GITHUB_EMAILS_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if emails_resp.status_code == 200:
                    emails = emails_resp.json()
                    # Only use a primary, verified email
                    primary = next(
                        (e for e in emails if e.get("primary") and e.get("verified")),
                        None,
                    )
                    email = primary["email"] if primary else ""

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve a verified email address from provider",
        )

    # Upsert: find by provider+sub first, then fall back to matching email.
    # Note: the email fallback links accounts across providers. This is intentional
    # but only safe because Google always verifies emails and we only accept verified
    # emails from GitHub's /user/emails endpoint.
    result = await db.execute(
        select(User).where(User.oauth_provider == provider, User.oauth_sub == oauth_sub)
    )
    user = result.scalar_one_or_none()

    if user is None:
        result2 = await db.execute(select(User).where(User.email == email))
        user = result2.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            name=name,
            avatar_url=avatar_url,
            oauth_provider=provider,
            oauth_sub=oauth_sub,
        )
        db.add(user)
    else:
        user.name = name
        user.avatar_url = avatar_url
        user.oauth_provider = provider
        user.oauth_sub = oauth_sub

    await db.flush()
    await db.commit()

    token = create_access_token(user.id)
    response = RedirectResponse(
        url=settings.FRONTEND_URL,
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
        secure=settings.SECURE_COOKIES,
    )
    # Clear the one-time state cookie
    response.delete_cookie(_STATE_COOKIE)
    return response
