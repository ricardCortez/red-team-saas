# Authentication Guide

Red Team SaaS supports three authentication methods: **JWT Bearer Token**, **API Key**, and **OAuth 2.0**.

---

## 1. JWT Bearer Token

### Obtain a Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "YourPassword123!"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Use the Token

Include the token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  http://localhost:8000/api/v1/projects
```

### Token Expiration

| Token          | Lifetime     |
|----------------|------------- |
| Access token   | 30 minutes   |
| Refresh token  | 7 days       |

### Refresh a Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIs..."}'
```

---

## 2. API Key

### Create an API Key

```bash
curl -X POST "http://localhost:8000/api/v1/security/api-keys" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "CI Pipeline", "scopes": ["read", "write"]}'
```

**Response:**
```json
{
  "id": 1,
  "key": "rtsa_abc123...",
  "name": "CI Pipeline",
  "scopes": ["read", "write"]
}
```

### Use the API Key

```bash
curl -H "Authorization: Bearer rtsa_abc123..." \
  http://localhost:8000/api/v1/projects
```

> API keys are prefixed with `rtsa_` and are handled by the security middleware.

---

## 3. OAuth 2.0 (Authorization Code Flow)

### Supported Providers

- GitHub
- Google

### Flow

1. **Redirect** the user to the authorization URL:
   ```
   GET /api/v1/security/oauth/authorize?provider=github
   ```

2. The provider redirects back with an **authorization code**.

3. **Exchange** the code for tokens:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/security/oauth/token" \
     -d '{"provider": "github", "code": "abc123"}'
   ```

---

## Rate Limit Headers

Every authenticated response includes rate-limit information:

| Header                | Description                              |
|-----------------------|------------------------------------------|
| `RateLimit-Limit`     | Maximum requests per minute              |
| `RateLimit-Remaining` | Remaining requests in current window     |
| `RateLimit-Reset`     | Unix timestamp when the window resets    |

When the limit is exceeded, a `429 Too Many Requests` response is returned with a `Retry-After` header (seconds).
