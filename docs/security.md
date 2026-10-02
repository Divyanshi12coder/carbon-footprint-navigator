# Security

| Concern | Implementation |
|---|---|
| Password storage | bcrypt (cost 12) via the `bcrypt` library; plain passwords never stored or logged. Policy: ≥ 8 chars with a letter and a digit (validated server-side, mirrored client-side). |
| Authentication | Stateless JWT (HS256, PyJWT) with `sub`, `exp`, `iat`, `type`, `tv`. Expiry configurable (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 12 h). |
| Logout / revocation | Each user has a `token_version`; logout and password change increment it, invalidating every previously issued token. |
| Timing attacks | Login with an unknown email still runs a bcrypt verification against a dummy hash. |
| Authorization | Every resource query filters by the authenticated user; foreign resources return 404 (not 403) to prevent id probing. Admin-only endpoints use a role dependency. Organization data requires membership. |
| Secrets | All secrets from environment variables (`DATABASE_URL`, `JWT_SECRET`, `AI_API_KEY`). In `ENVIRONMENT=production` the app refuses to start with the default or a < 32-character JWT secret. Only `.env.example` files with placeholders are committed; `.gitignore` excludes `.env*`. |
| LLM key | Used only by the backend provider adapter. The frontend never sees it and never calls the LLM. |
| CORS | Explicit allow-list from `CORS_ORIGINS`; credentials not allowed (bearer tokens, no cookies). Unknown origins fail preflight. |
| Input validation | Pydantic schemas (types, ranges, enums, lengths), catalogue validation of activity details, date bounds (no future dates). |
| SQL injection | SQLAlchemy ORM / expression API only; no string-built SQL with user input. |
| Rate limiting | Sliding-window limiter: login/register per IP (`RATE_LIMIT_AUTH_PER_MINUTE`, default 10), assistant per user (default 12). In-process — use Redis for multi-instance deployments. |
| Headers | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy` on API responses; nginx adds the same for the SPA. |
| Errors | Unhandled exceptions are logged server-side and returned as a generic 500 without stack traces. |
| Containers | Backend runs as a non-root user; images contain no secrets. |
| File uploads | None — the platform does not accept file uploads. |

## Token storage trade-off

The SPA stores the access token in `localStorage` so the backend can stay stateless and cross-origin (Vercel → Render).
This is exposed to XSS; mitigations are React's escaping, no `dangerouslySetInnerHTML` (the assistant renders a safe markdown
subset), no third-party scripts besides Google Fonts, and short-ish token expiry with server-side revocation. A cookie-based
session with CSRF protection would be the next hardening step.
