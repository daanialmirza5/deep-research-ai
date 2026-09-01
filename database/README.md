# Database

- **Source of truth for schema changes**: [`backend/alembic/versions/`](../backend/alembic/versions/).
  Every schema change is a reviewed Alembic migration generated from the SQLAlchemy models in
  [`backend/app/models/`](../backend/app/models/).
- **[`schema.sql`](schema.sql)**: a generated, human-readable snapshot of what `alembic upgrade head`
  produces — for reviewing the schema in a PR without reading Alembic's diff syntax. Not
  hand-edited; regenerate with:
  ```bash
  pg_dump --schema-only --no-owner --no-privileges "$DATABASE_URL" > database/schema.sql
  ```
- **[`seeds/`](seeds/)**: development seed data, loaded via `make seed`.

Full schema design and rationale: [`docs/database-schema.md`](../docs/database-schema.md).

Note on scope vs. the original Phase 1 plan: `docs/folder-structure.md` originally sketched a
`database/migrations/` directory mirroring `backend/alembic/versions/`. Built in Phase 4, that
turned out to be pure duplication with no independent value — two copies of the same migrations
drifting out of sync is worse than one. `schema.sql` (a derived, reviewable artifact) replaces it.
