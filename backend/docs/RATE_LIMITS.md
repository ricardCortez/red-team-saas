# Rate Limits

Red Team SaaS uses a **token-bucket** rate limiter. Each authenticated user has an independent bucket per endpoint.

---

## Default Limits

| Parameter      | Value   |
|--------------- |---------|
| Requests/min   | 60      |
| Burst capacity | 100     |

---

## Per-Endpoint Limits

| Endpoint               | Requests/min |
|------------------------|------------- |
| `/auth/login`          | 5            |
| `/tools/execute`       | 10           |
| `/findings`            | 30           |
| `/reports/generate`    | 5            |
| All other endpoints    | 60 (default) |

---

## Rate Limit Headers

Every response includes the following headers:

| Header                | Type   | Description                                  |
|-----------------------|--------|----------------------------------------------|
| `RateLimit-Limit`     | string | Maximum requests allowed per minute           |
| `RateLimit-Remaining` | string | Tokens remaining in the current window        |
| `RateLimit-Reset`     | string | Unix timestamp when the bucket fully refills  |

---

## Handling 429 Responses

When you exceed the rate limit, the API returns:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 12
Content-Type: application/json

{"detail": "Rate limit exceeded"}
```

### Recommended Retry Strategy

Use exponential backoff:

```python
import time
import requests

def request_with_backoff(url, headers, max_retries=5):
    for attempt in range(max_retries):
        resp = requests.get(url, headers=headers)
        if resp.status_code != 429:
            return resp
        wait = int(resp.headers.get("Retry-After", 2 ** attempt))
        time.sleep(wait)
    raise Exception("Rate limit exceeded after retries")
```

---

## Increasing Limits

Custom rate limits can be configured per user by an administrator via the security API:

```bash
curl -X POST "http://localhost:8000/api/v1/security/rate-limit-config" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"user_id": 42, "requests_per_minute": 120, "burst_capacity": 200}'
```

For enterprise limit increases, contact support.
