"""Domain exceptions raised by services. Routers (app/api/v1/*) catch these
and translate them to HTTP responses — services themselves never raise
HTTPException, so they stay usable outside a request context (scripts,
tests, future non-HTTP entrypoints).
"""


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class OAuthProviderNotConfiguredError(Exception):
    pass


class ProjectNotFoundError(Exception):
    """Raised both when a project truly doesn't exist and when it exists but
    belongs to a different user — deliberately not distinguished (routers
    map both to 404, not 403) so a client can't enumerate other users'
    project ids by observing a 403-vs-404 difference."""


class ResearchSessionNotFoundError(Exception):
    """Same non-disclosure rationale as ProjectNotFoundError."""


class DocumentNotFoundError(Exception):
    """Same non-disclosure rationale as ProjectNotFoundError."""
