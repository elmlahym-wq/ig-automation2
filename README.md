# Instagram Comment-to-DM Automation

[![Python checks](https://github.com/elmlahym-wq/ig-automation2/actions/workflows/ci.yml/badge.svg)](https://github.com/elmlahym-wq/ig-automation2/actions/workflows/ci.yml)

A **single-operator campaign dashboard** that turns keyword-matching Instagram comments into a public reply and a private message through the official Meta Graph API.

Built with **Python, FastAPI, SQLAlchemy, Jinja2, and vanilla JavaScript**. SQLite supports local development; PostgreSQL supports hosted deployments.

## What it does

- Create, edit, pause, and delete keyword campaigns for individual posts.
- Preview post details before saving a campaign.
- Personalize reply templates with `{username}`.
- Verify webhook signatures and process events in background tasks.
- Reserve comment IDs with a database uniqueness constraint to avoid duplicate processing.
- Send public replies and private replies independently, with bounded retries for transient API failures.
- Keep credential values out of API responses and application logs.

> This repository contains application code and placeholder configuration. Meta credentials, database passwords, and deployment settings belong in your hosting environment or an untracked local `.env` file.

## Example campaign

| Setting | Example |
| --- | --- |
| Name | Resource guide |
| Trigger keywords | `guide, link, info` |
| Public reply | `Thanks! Check your DMs.` |
| Private message | `Hi {username}, here's your guide: https://example.com/guide` |

Keywords use case-insensitive substring matching. No real account or token is needed to run the automated tests.

## Quick start

Use **Python 3.12**.

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
```

Generate a local password:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put it in `DASHBOARD_PASSWORD` inside `.env`, then run:

```bash
uvicorn main:app --reload --no-access-log
```

Open http://localhost:8000/dashboard and sign in with `DASHBOARD_USER` (default `admin`) and your password. You can explore campaign management locally without Instagram credentials. Outbound Instagram actions require your own properly configured Meta application and account.

The dashboard and management API **deny access when no password is configured**, including in local development.

## Configuration

| Variable | Purpose |
| --- | --- |
| `DASHBOARD_PASSWORD` | Required dashboard/API password |
| `DASHBOARD_USER` | Dashboard username; defaults to `admin` |
| `APP_ORIGIN` | Public HTTPS origin for browser origin checks, especially behind a proxy |
| `DATABASE_URL` | SQLite locally; PostgreSQL connection string in production |
| `FACEBOOK_APP_SECRET` | Validates signed webhook requests |
| `WEBHOOK_VERIFY_TOKEN` | Verifies the webhook subscription handshake |
| `INSTAGRAM_ACCESS_TOKEN` | Preferred server-side Graph API token |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Instagram account used for private replies |
| `GRAPH_API_VERSION` | Configurable Graph API version; defaults to `v21.0` |

Environment credentials take priority over legacy dashboard-saved credentials. The legacy settings form stores an access token in the database as plaintext; use environment-based credentials and restrict database access for hosted deployments.

## Project structure

| Path | Responsibility |
| --- | --- |
| `app/main.py` | App setup, route registration, and browser security headers |
| `app/routes/` | Dashboard, management API, authentication, and webhook endpoints |
| `app/instagram.py` | Graph API client and bounded retry handling |
| `app/database.py` | Database engine and session lifecycle |
| `app/models.py` | Campaigns, configuration, and comment deduplication |
| `templates/` | Server-rendered dashboard pages |
| `static/` | Dashboard JavaScript and styles |
| `tests/` | Isolated security and behavior regression tests |
| `scripts/` | Working-tree secret checks |
| `docs/` | Architecture and deployment notes |
| `main.py` | Compatibility entry point for `uvicorn main:app` |

## Checks

```bash
python -m unittest discover -s tests -v
python scripts/check_secrets.py
pip install pip-audit
pip-audit -r requirements.txt
```

GitHub Actions runs tests, working-tree secret checks, and dependency auditing on pushes and pull requests. The secret check uses targeted patterns; it does not certify that a repository or its history is free of every possible secret.

## Deployment

Docker, Render, and Railway configuration files are included. Configure credentials in the hosting dashboard, use HTTPS, set `APP_ORIGIN`, and use PostgreSQL or persistent database storage. `/health` is the public health check. Interactive API docs are disabled.

```bash
docker build -t comment-dm .
docker run --rm -p 8000:8000 --env-file .env comment-dm
```

See [deployment](docs/DEPLOYMENT.md), [architecture](docs/ARCHITECTURE.md), and [security notes](SECURITY.md).

## Integration boundaries

The client uses the Facebook Graph host and the Facebook Login account model. Confirm permissions, supported API versions, webhook subscriptions, account eligibility, and private-reply limits in [Meta's current documentation](https://developers.facebook.com/docs/instagram-platform/) before connecting a live account. This project does not implement OAuth token acquisition or renewal.

This is a single-operator application, not a multi-tenant service. Background tasks run in the web process. Reserving a comment before sending prevents repeated processing, but a crash can leave an incomplete action; there is no durable queue or automatic recovery. Outbound retries cannot guarantee exactly-once delivery. Authentication throttling is process-local. See the architecture notes for production considerations.

## License

No open-source license has been assigned to this repository.
