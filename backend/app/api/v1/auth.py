"""Auth endpoints — see docs/api-design.md § Auth for the contract these
implement. Routers translate app.services.exceptions into HTTP responses;
the service layer itself never raises HTTPException.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_auth_service, get_container
from app.core.container import Container
from app.core.rate_limit import limiter
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair, UserCreate
from app.schemas.user import UserRead
from app.services.auth_service import AuthService
from app.services.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    OAuthProviderNotConfiguredError,
)

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    body: UserCreate,
    service: AuthService = Depends(get_auth_service),
) -> object:
    try:
        return await service.register(body.email, body.password, body.full_name)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered"
        ) from exc


@router.post("/login", response_model=TokenPair)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    try:
        user = await service.authenticate(body.email, body.password)
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        ) from exc
    return await service.issue_token_pair(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    try:
        return await service.refresh(body.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        ) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.logout(body.refresh_token)


@router.get("/oauth/{provider}")
async def oauth_login(
    request: Request,
    provider: str,
    container: Container = Depends(get_container),
) -> object:
    # types-Authlib doesn't type OAuth.create_client's return (stub gap, not
    # ours to fix) — narrow, targeted ignore rather than loosening strict
    # mode for the whole module.
    client = container.oauth.create_client(provider)  # type: ignore[no-untyped-call]
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OAuth provider '{provider}' is unknown or not configured",
        )
    base_url = container.settings.oauth_redirect_base_url
    redirect_uri = f"{base_url}/api/v1/auth/oauth/{provider}/callback"
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/oauth/{provider}/callback", response_model=TokenPair)
async def oauth_callback(
    request: Request,
    provider: str,
    container: Container = Depends(get_container),
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    # types-Authlib doesn't type OAuth.create_client's return (stub gap, not
    # ours to fix) — narrow, targeted ignore rather than loosening strict
    # mode for the whole module.
    client = container.oauth.create_client(provider)  # type: ignore[no-untyped-call]
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OAuth provider '{provider}' is unknown or not configured",
        )

    token = await client.authorize_access_token(request)

    try:
        oauth_id, email, full_name = await _extract_oauth_profile(provider, client, token)
    except OAuthProviderNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported provider: {provider}"
        ) from exc

    user = await service.get_or_create_oauth_user(provider, oauth_id, email, full_name)
    # NOTE: returning the token pair directly as JSON is a placeholder for a
    # backend with no frontend yet (Phase 6). A browser-based SPA flow
    # typically redirects here to a frontend route with a short-lived
    # one-time code that the frontend exchanges for tokens, rather than
    # putting tokens in a redirect URL — revisit this in Phase 6.
    return await service.issue_token_pair(user)


async def _extract_oauth_profile(
    provider: str, client: Any, token: dict[str, Any]
) -> tuple[str, str, str]:
    # authlib's remote-app client and OAuth token/profile payloads are
    # inherently dynamic (arbitrary provider JSON) — `Any` here is a
    # deliberate, narrow type-erasure boundary, not a strictness gap.
    if provider == "google":
        return await _extract_google_profile(client, token)
    if provider == "github":
        return await _extract_github_profile(client, token)
    raise OAuthProviderNotConfiguredError(provider)


async def _extract_google_profile(client: Any, token: dict[str, Any]) -> tuple[str, str, str]:
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await client.userinfo(token=token)
    email = str(userinfo["email"])
    return str(userinfo["sub"]), email, str(userinfo.get("name", email))


async def _extract_github_profile(client: Any, token: dict[str, Any]) -> tuple[str, str, str]:
    profile_resp = await client.get("user", token=token)
    profile = profile_resp.json()
    email: str | None = profile.get("email")
    if not email:
        emails_resp = await client.get("user/emails", token=token)
        email = next((e["email"] for e in emails_resp.json() if e["primary"]), None)
    full_name = profile.get("name") or profile["login"]
    return str(profile["id"]), str(email), str(full_name)
