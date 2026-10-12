# Deployment

## Required runtime settings

Use the names in `.env.example`; enter real values through your host's secret/environment settings. Set a strong `DASHBOARD_PASSWORD` and the public HTTPS `APP_ORIGIN`. To process Instagram webhooks, configure `FACEBOOK_APP_SECRET`, `WEBHOOK_VERIFY_TOKEN`, `INSTAGRAM_ACCESS_TOKEN`, and `INSTAGRAM_BUSINESS_ACCOUNT_ID`.

For hosted storage, set `DATABASE_URL` to your provider's PostgreSQL connection string. Copy the exact host and port from the provider; URL-encode special characters in the password. The app accepts `postgresql://` and uses psycopg internally. Select the provider's recommended TLS settings.

## Render and Railway

`render.yaml` prompts for runtime values without embedding them in source. `railway.toml` uses the Dockerfile and `/health` checks. Add runtime variables through Railway's deployment settings. Configuration files are examples, not confirmation of an active deployment.

The image runs as a non-root user. Its working directory is writable for local SQLite use; an ephemeral container filesystem does not persist database contents across replacement.

## Meta connection

Use the Facebook Login integration expected by `app/instagram.py`. Configure a webhook callback at `https://YOUR-DOMAIN/webhook/instagram`, using the same verification token as the server. Consult [Meta's official documentation](https://developers.facebook.com/docs/instagram-platform/) for current app permissions, reviews, webhook fields, API versions, and account eligibility. Configure a supported `GRAPH_API_VERSION` for your app.

Tokens are supplied by the operator; acquisition and renewal are not implemented here. Environment tokens override dashboard-saved tokens. The dashboard configuration endpoint reveals only whether a token is configured, never its value or suffix.

## Logging

The supplied container command disables Uvicorn access logging because verification requests carry the webhook verification token in a query string. If you enable proxy/server access logs, redact query strings and authorization headers. Do not enable HTTP wire/debug logging or log request bodies from settings endpoints.

## Updating an existing deployment

The `main:app` entry point remains compatible. Dashboard access now requires a password even in development. Configure `APP_ORIGIN` when behind a reverse proxy. Set environment credentials if you want them to override legacy database configuration. Updating source does not rotate credentials at Meta or your database provider.
