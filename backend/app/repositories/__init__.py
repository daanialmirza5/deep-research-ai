"""Data access layer. The only layer that knows SQLAlchemy query shape;
services depend on repositories, never on models directly.
See docs/architecture.md § 4 (clean architecture layering)."""
