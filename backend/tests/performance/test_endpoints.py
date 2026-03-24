"""
Performance tests – basic latency assertions.

SLA targets (SQLite in-memory is slower than prod PostgreSQL, so thresholds
are 5× the production target to avoid false positives in CI):
  - health / root:   <500 ms
  - register / login: <1000 ms
"""
import time


def _elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


class TestHealthPerformance:
    def test_health_under_500ms(self, client):
        t = time.perf_counter()
        resp = client.get("/health")
        ms = _elapsed_ms(t)
        assert resp.status_code == 200
        assert ms < 500, f"Health check took {ms:.1f} ms (limit 500 ms)"

    def test_root_under_500ms(self, client):
        t = time.perf_counter()
        resp = client.get("/")
        ms = _elapsed_ms(t)
        assert resp.status_code == 200
        assert ms < 500, f"Root endpoint took {ms:.1f} ms (limit 500 ms)"


class TestAuthPerformance:
    def test_register_under_1000ms(self, client, test_user_data):
        t = time.perf_counter()
        resp = client.post("/api/v1/auth/register", json=test_user_data)
        ms = _elapsed_ms(t)
        assert resp.status_code == 201
        assert ms < 1000, f"Register took {ms:.1f} ms (limit 1000 ms)"

    def test_login_under_1000ms(self, client, test_user_data, registered_user):
        t = time.perf_counter()
        resp = client.post(
            "/api/v1/auth/login",
            params={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        ms = _elapsed_ms(t)
        assert resp.status_code == 200
        assert ms < 1000, f"Login took {ms:.1f} ms (limit 1000 ms)"

    def test_me_under_500ms(self, client, auth_token):
        t = time.perf_counter()
        resp = client.get("/api/v1/auth/me", params={"token": auth_token})
        ms = _elapsed_ms(t)
        assert resp.status_code == 200
        assert ms < 500, f"/me took {ms:.1f} ms (limit 500 ms)"

    def test_refresh_under_500ms(self, client, refresh_token_value):
        t = time.perf_counter()
        resp = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": refresh_token_value},
        )
        ms = _elapsed_ms(t)
        assert resp.status_code == 200
        assert ms < 500, f"Refresh took {ms:.1f} ms (limit 500 ms)"

    def test_ten_consecutive_health_checks_stable(self, client):
        """Latency must not degrade under repeated requests."""
        times = []
        for _ in range(10):
            t = time.perf_counter()
            client.get("/health")
            times.append(_elapsed_ms(t))
        avg = sum(times) / len(times)
        assert avg < 200, f"Average health latency {avg:.1f} ms over 10 calls (limit 200 ms)"
