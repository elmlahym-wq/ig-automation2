# Security notes

Never publish live API tokens, application secrets, database connection passwords, or dashboard credentials. Use hosting environment settings or a local `.env` excluded from version control. `.env.example` contains empty secret fields only.

If a credential was published, revoke or rotate it at its provider, update the deployment, and check provider access logs. Deleting a file from the current branch does not remove it from older commits, caches, forks, or existing clones. History cleanup complements credential rotation; it cannot make an exposed credential trustworthy again.

Do not include real credentials in public issues or pull requests. Security changes should include regression tests and avoid exposing secrets in logs, exception messages, API responses, or deployment examples.

## Runtime safeguards and limits

Dashboard/API access fails closed without a configured password. Use HTTPS. Origin checks protect browser mutations, while webhook POSTs use raw-body HMAC signatures. Request sizes are bounded for webhook processing. Access tokens are sent in Authorization headers; sensitive Graph response bodies are not logged.

Dashboard-saved tokens remain plaintext in the legacy database table. Prefer environment credentials, restrict database access, and remove obsolete saved tokens after migrating. Database backups may also contain credentials. Process-local login throttling does not replace edge rate limiting across multiple workers.

The included secret-check script catches selected known patterns in publishable files. It does not scan historical Git objects and is not a comprehensive secret scanner. Consider GitHub secret scanning and push protection where available.
