"""authlib OAuth client registry — Google and GitHub, registered only when
their credentials are configured (see .env.example). Registration itself
makes no network calls (Google's OIDC discovery document is fetched lazily,
on first authorize/callback), so building this at container startup is safe
even with no providers configured — `create_client(provider)` simply returns
None and the router responds with a clean error instead of every request
needing its own try/except around a missing config.
"""

from authlib.integrations.starlette_client import OAuth

from app.core.config import Settings


def build_oauth_registry(settings: Settings) -> OAuth:
    oauth = OAuth()

    if settings.google_client_id and settings.google_client_secret:
        oauth.register(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    if settings.github_oauth_client_id and settings.github_oauth_client_secret:
        oauth.register(
            name="github",
            client_id=settings.github_oauth_client_id,
            client_secret=settings.github_oauth_client_secret,
            access_token_url="https://github.com/login/oauth/access_token",
            authorize_url="https://github.com/login/oauth/authorize",
            api_base_url="https://api.github.com/",
            client_kwargs={"scope": "user:email"},
        )

    return oauth
