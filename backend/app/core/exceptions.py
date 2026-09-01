"""Framework-agnostic exceptions raised by app.core modules (currently just
security.py). Kept separate from app.services.exceptions so app/core/ never
has to import from app/services/ — see docs/architecture.md's layering.
"""


class InvalidTokenError(Exception):
    """Raised when a JWT is malformed, expired, or not an access token."""
