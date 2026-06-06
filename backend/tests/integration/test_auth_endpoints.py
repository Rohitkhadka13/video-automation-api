# =============================================================================
# tests/integration/test_auth_endpoints.py
# Integration tests for /api/v1/auth/* endpoints using a real test DB.
# =============================================================================
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.auth]


class TestLoginEndpoint:

    async def test_valid_login_returns_tokens(
        self, client: AsyncClient, test_user
    ):
        response = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            "password": "Testpass1!",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_wrong_password_returns_401(
        self, client: AsyncClient, test_user
    ):
        response = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            "password": "WrongPassword1!",
        })
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    async def test_nonexistent_email_returns_401(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@nowhere.com",
            "password": "SomePass1!",
        })
        assert response.status_code == 401

    async def test_missing_fields_returns_422(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            # missing password
        })
        assert response.status_code == 422

    async def test_invalid_email_format_returns_422(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "Testpass1!",
        })
        assert response.status_code == 422


class TestRefreshEndpoint:

    async def test_valid_refresh_token_returns_new_pair(
        self, client: AsyncClient, test_user
    ):
        # Login first
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            "password": "Testpass1!",
        })
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should differ from the old one (rotation)
        assert data["refresh_token"] != refresh_token

    async def test_access_token_as_refresh_returns_401(
        self, client: AsyncClient, test_user
    ):
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            "password": "Testpass1!",
        })
        access_token = login_resp.json()["access_token"]

        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": access_token
        })
        assert response.status_code == 401

    async def test_garbage_token_returns_401(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "not.a.real.jwt"
        })
        assert response.status_code == 401


class TestLogoutEndpoint:

    async def test_logout_returns_204(
        self, client: AsyncClient, auth_headers
    ):
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 204

    async def test_logout_without_token_returns_401(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    async def test_refresh_after_logout_returns_401(
        self, client: AsyncClient, test_user
    ):
        """After logout, the refresh token must be invalidated."""
        # Login
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            "password": "Testpass1!",
        })
        tokens = login_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # Logout
        await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Attempt to refresh — must fail
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 401


class TestGetMeEndpoint:

    async def test_authenticated_user_gets_profile(
        self, client: AsyncClient, test_user, auth_headers
    ):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["full_name"] == "Test User"
        assert "hashed_password" not in data

    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestRegistrationEndpoint:

    async def test_register_new_user(self, client: AsyncClient):
        response = await client.post("/api/v1/users/", json={
            "email": "newuser@example.com",
            "password": "NewPass1!",
            "full_name": "New User",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "hashed_password" not in data

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, test_user
    ):
        response = await client.post("/api/v1/users/", json={
            "email": "testuser@example.com",   # already exists
            "password": "Another1!",
            "full_name": "Duplicate",
        })
        assert response.status_code == 409

    async def test_weak_password_returns_422(self, client: AsyncClient):
        response = await client.post("/api/v1/users/", json={
            "email": "weak@example.com",
            "password": "short",   # no uppercase, no digit, too short
            "full_name": "Weak",
        })
        assert response.status_code == 422

    async def test_password_without_uppercase_returns_422(self, client: AsyncClient):
        response = await client.post("/api/v1/users/", json={
            "email": "noup@example.com",
            "password": "nouppercase1!",
            "full_name": "No Upper",
        })
        assert response.status_code == 422

    async def test_new_user_can_login_after_registration(self, client: AsyncClient):
        # Register
        await client.post("/api/v1/users/", json={
            "email": "fresh@example.com",
            "password": "FreshPass1!",
            "full_name": "Fresh User",
        })
        # Login
        response = await client.post("/api/v1/auth/login", json={
            "email": "fresh@example.com",
            "password": "FreshPass1!",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()