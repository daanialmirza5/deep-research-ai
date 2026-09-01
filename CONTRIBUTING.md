# Contributing to DeepResearch AI

Thanks for your interest in contributing. This project is being built in explicit, sequential
phases (see [docs/milestones.md](docs/milestones.md)) — please check which phase is currently
active before proposing work that depends on a later phase's foundations.

## Development setup

Full instructions: [docs/installation.md](docs/installation.md) (local dev, no Docker required) or
[docs/deployment.md](docs/deployment.md) (the full stack via Docker Compose). Quick version:

```bash
git clone <repo-url>
cd deep-research-ai
cp .env.example .env        # fill in required values
make install                 # backend (+ai) and frontend dependencies, locally
make up                      # start the full stack via Docker Compose
make migrate && make seed
```

Common tasks are exposed via the `Makefile` — run `make help` for the full list (`make test`,
`make lint`, `make migrate`, `make logs`, ...).

## Branching

- `main` is always deployable.
- Feature branches: `feature/<short-description>` (e.g. `feature/fact-checker-agent`).
- Fix branches: `fix/<short-description>`.
- One logical change per PR — split unrelated changes into separate PRs.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <summary>

feat(ai): add fact-checker revision loop
fix(backend): correct refresh token rotation
docs(readme): update architecture diagram
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`.

## Pull requests

- Reference the phase/milestone the change belongs to.
- Include tests for new backend/`ai` logic (`pytest`) and frontend logic (component tests).
- CI (`.github/workflows/ci.yml`: ruff, mypy --strict, pytest, eslint, tsc, vitest, `next build`)
  must pass before merge.
- Update `docs/` alongside any change that alters architecture, schema, or API surface — this
  repository treats stale docs as a bug, not a nitpick (see `docs/api-design.md` and
  `docs/architecture.md`'s Phase 14 revisions for what that audit actually looked like).

## Code style

- **Python**: type hints on every public function, `ruff` for lint/format. Comments explain *why*,
  not *what* — a non-obvious constraint, a workaround for a specific bug, something that would
  surprise a reader — not a restatement of what well-named code already shows; see any file under
  `backend/app/` or `ai/` for the convention in practice.
- **TypeScript**: strict mode, no implicit `any`, `eslint` + `prettier`.
- No commented-out code, no unused exports, no TODO comments without a linked issue.

## Reporting bugs / requesting features

Use the GitHub issue templates under `.github/ISSUE_TEMPLATE/` (added in Phase 15). Until then,
open a plain issue with: expected behavior, actual behavior, repro steps, and environment (local
Docker vs. cloud deploy).
