# Architecture

## Request flow

1. The server reads environment settings and initializes SQLAlchemy tables at startup.
2. Dashboard pages and `/api/*` management endpoints share HTTP Basic authentication.
3. A webhook POST is read with a 256,000-byte limit, authenticated against the raw-body HMAC signature, and validated for expected JSON container types.
4. A background task matches the post and comment text to an active campaign.
5. A unique comment record is committed before either outbound action.
6. The Graph API client sends a public reply and a private reply independently. A non-sensitive result is saved for each action.

## Stored data

| Table | Contents |
| --- | --- |
| `campaigns` | Post IDs, keyword lists, reply templates, enabled status, owner label |
| `processed_comments` | Comment IDs, campaign reference, status, processing time |
| `config` | Legacy account identifiers and a dashboard-saved access token |

The owner label is metadata, not a tenant isolation boundary. All authenticated users of this deployment share the same data.

Environment access tokens and account IDs override the legacy configuration row. Tokens are not returned by the management API; legacy database storage is not encrypted by the application.

## Security boundaries

- Public `/health` returns only an application status.
- GET webhook verification compares a configured verification token.
- Webhook POSTs require a configured app secret and valid signature.
- Dashboard/API requests require a configured password in every environment.
- Browser mutations reject mismatched origins; `APP_ORIGIN` defines the canonical hosted origin.
- Graph access tokens travel in an Authorization header, not URL parameters.
- Raw API response bodies and exception text are excluded from app logs and stored statuses.
- Swagger, ReDoc, and public OpenAPI endpoints are disabled.

## Deployment limitations

SQLite needs a writable, persistent location for durable hosted data. PostgreSQL is recommended for container hosts. Table creation is automatic; schema migration management is not implemented.

Authentication throttling lives in each worker's memory. Behind a proxy, trusted client-IP forwarding and shared rate limiting need deployment-specific configuration. Use HTTPS for Basic authentication and do not expose database credentials to frontend clients.

FastAPI background tasks and pre-send deduplication provide at-most-once processing attempts, not durable or exactly-once message delivery. A durable queue, action-level state machine, and reconciliation workflow are future improvements.
