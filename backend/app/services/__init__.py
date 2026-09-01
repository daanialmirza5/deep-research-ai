"""Business logic layer. Services call repositories and the ai/ package;
they never construct HTTP responses or touch SQLAlchemy directly.
See docs/architecture.md § 4 (clean architecture layering)."""
