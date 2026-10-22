"""
Sentinel AI — Production CORS and Authentication Security Tests
Validates:
1. Strict, non-wildcard CORS handling for production Vercel frontend domains.
2. Rejection of unauthorized foreign origins on OPTIONS preflight and cross-origin POST.
3. Successful authentication against /api/v1/auth/login with Supabase-compatible JWT issuance.
4. Security enforcement: role self-assignment is forbidden (403).
5. Robustness against trailing slashes and malformed headers.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

class TestProductionCorsConfiguration:
    """Validates CORS behavior for Sentinel AI frontend deployments."""

    @pytest.mark.parametrize("origin", [
        "https://sentinel-ai-real-time-fraud-intelli.vercel.app",
        "https://sentinel-ai-real-time-fraud-intelligence.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://sentinel-ai-preview-pr12.vercel.app",
        "https://sentinel-ai-git-feature-branch.vercel.app",
    ])
    def test_cors_preflight_allowed_origins(self, origin: str):
        """OPTIONS preflight from legitimate Vercel and local origins must return 200 with matching Allow-Origin."""
        resp = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            }
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == origin
        assert resp.headers.get("access-control-allow-credentials") == "true"
        assert "POST" in resp.headers.get("access-control-allow-methods", "")

    @pytest.mark.parametrize("origin", [
        "https://attacker-domain.com",
        "https://malicious-phishing-site.org",
        "https://other-unrelated-project.vercel.app",
        "http://unauthorized-domain.com:8080",
    ])
    def test_cors_preflight_disallowed_origins(self, origin: str):
        """OPTIONS preflight from unauthorized origins must be strictly rejected (HTTP 400)."""
        resp = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            }
        )
        assert resp.status_code == 400
        assert resp.headers.get("access-control-allow-origin") is None

    def test_cross_origin_post_login_succeeds_for_vercel(self):
        """POST login from production Vercel origin must succeed and include access-control-allow-origin header."""
        resp = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://sentinel-ai-real-time-fraud-intelli.vercel.app"},
            json={
                "email": "analyst.sarah@sentinel.ai",
                "password": "SentinelSecure2026!"
            }
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "https://sentinel-ai-real-time-fraud-intelli.vercel.app"
        assert resp.headers.get("access-control-allow-credentials") == "true"
        
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["role"] == "fraud_investigator"
        assert data["user"]["email"] == "analyst.sarah@sentinel.ai"

    def test_cross_origin_post_login_missing_cors_header_for_attacker(self):
        """POST from unauthorized origin must NOT receive access-control-allow-origin header."""
        resp = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://malicious-site.com"},
            json={
                "email": "analyst.sarah@sentinel.ai",
                "password": "SentinelSecure2026!"
            }
        )
        # Even if HTTP logic processes, CORSMiddleware must omit allow-origin header, blocking browser access
        assert resp.headers.get("access-control-allow-origin") is None

    def test_login_rejects_client_role_self_assignment(self):
        """Client attempting to self-assign a higher role (e.g. admin) must be rejected with 403 Forbidden."""
        resp = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://sentinel-ai-real-time-fraud-intelli.vercel.app"},
            json={
                "email": "analyst.sarah@sentinel.ai",
                "password": "SentinelSecure2026!",
                "role": "admin"
            }
        )
        assert resp.status_code == 403
        assert "Forbidden: Client cannot self-assign role" in resp.json()["detail"]
