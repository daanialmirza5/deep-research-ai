# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in DeepResearch AI, please **do not** open a public
GitHub issue. Instead:

1. Open a [GitHub Security Advisory](../../security/advisories/new) (private) on this repository, or
2. If that's unavailable, open an issue titled `[SECURITY] contact request` with no technical
   detail, and a maintainer will follow up with a private channel.

Please include:
- A description of the vulnerability and its potential impact
- Steps to reproduce (a minimal repro is ideal)
- Any known mitigations

We aim to acknowledge reports within **5 business days** and to ship a fix or mitigation plan
within **30 days** for confirmed high/critical issues.

## Supported Versions

This project is pre-1.0 (see [CHANGELOG.md](CHANGELOG.md)/[milestones.md](docs/milestones.md) for
current phase). Security fixes land on the `main` branch only until a stable `1.x` line exists.

## Scope

In scope: the FastAPI backend, Celery workers, the `ai/` agent package, the Next.js frontend, and
the Docker Compose deployment configuration in this repository.

Out of scope: vulnerabilities in third-party services this project integrates with (OpenAI,
Anthropic, search providers) — report those to the respective vendor.

## Handling of Secrets

- Never commit `.env` files, API keys, or credentials — see `.env.example` for the full list of
  expected variables and `.gitignore` for what's excluded.
- User-provided third-party API keys (Settings → API Keys) are stored encrypted at rest
  (see [database-schema.md § api_keys](docs/database-schema.md)).
