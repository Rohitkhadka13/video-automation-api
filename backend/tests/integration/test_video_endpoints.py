# =============================================================================
# tests/integration/test_video_endpoints.py
# Integration tests for project + video endpoints.
# =============================================================================
from __future__ import annotations

import io
from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.video]


# =============================================================================
# Project endpoints
# =============================================================================

class TestProjectEndpoints:

    async def test_create_project(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/projects/",
            json={"name": "My Test Project", "description": "A project for testing"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Test Project"
        assert data["slug"] == "my-test-project"
        assert data["video_count"] == 0
        assert "id" in data

    async def test_list_projects_returns_own_projects(
        self, client: AsyncClient, auth_headers
    ):
        # Create two projects
        for i in range(2):
            await client.post(
                "/api/v1/projects/",
                json={"name": f"Project {i}"},
                headers=auth_headers,
            )

        response = await client.get("/api/v1/projects/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert all("id" in p for p in data["items"])

    async def test_get_project_by_id(self, client: AsyncClient, auth_headers):
        create_resp = await client.post(
            "/api/v1/projects/",
            json={"name": "Specific Project"},
            headers=auth_headers,
        )
        project_id = create_resp.json()["id"]

        response = await client.get(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == project_id

    async def test_get_other_users_project_returns_404(
        self, client: AsyncClient, auth_headers, admin_headers
    ):
        # Admin creates a project
        create_resp = await client.post(
            "/api/v1/projects/",
            json={"name": "Admin Project"},
            headers=admin_headers,
        )
        project_id = create_resp.json()["id"]

        # Regular user tries to access it
        response = await client.get(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_update_project(self, client: AsyncClient, auth_headers):
        create_resp = await client.post(
            "/api/v1/projects/",
            json={"name": "Original Name"},
            headers=auth_headers,
        )
        project_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "Updated Name", "description": "New description"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    async def test_delete_project(self, client: AsyncClient, auth_headers):
        create_resp = await client.post(
            "/api/v1/projects/",
            json={"name": "To Be Deleted"},
            headers=auth_headers,
        )
        project_id = create_resp.json()["id"]

        delete_resp = await client.delete(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
        )
        assert delete_resp.status_code == 200

        # Project should no longer be accessible
        get_resp = await client.get(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404

    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/projects/")
        assert response.status_code == 401


# =============================================================================
# Video endpoints
# =============================================================================

class TestVideoEndpoints:

    async def _create_project(
        self, client: AsyncClient, headers: dict
    ) -> str:
        """Helper: create a project and return its ID."""
        resp = await client.post(
            "/api/v1/projects/",
            json={"name": f"Project {uuid4().hex[:6]}"},
            headers=headers,
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_create_video_record(self, client: AsyncClient, auth_headers):
        project_id = await self._create_project(client, auth_headers)

        response = await client.post(
            f"/api/v1/videos/projects/{project_id}/videos",
            json={
                "title": "My First Video",
                "description": "Test description",
                "script_prompt": "Make it engaging",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My First Video"
        assert data["status"] == "pending"
        assert data["project_id"] == project_id

    async def test_upload_video_file(
        self, client: AsyncClient, auth_headers, mock_storage
    ):
        project_id = await self._create_project(client, auth_headers)

        # Create video record
        create_resp = await client.post(
            f"/api/v1/videos/projects/{project_id}/videos",
            json={"title": "Upload Test"},
            headers=auth_headers,
        )
        video_id = create_resp.json()["id"]

        # Upload file
        fake_video = io.BytesIO(b"fake video content" * 1000)
        response = await client.post(
            f"/api/v1/videos/{video_id}/upload",
            files={"file": ("test.mp4", fake_video, "video/mp4")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "uploaded"

    async def test_upload_oversized_file_returns_413(
        self, client: AsyncClient, auth_headers
    ):
        project_id = await self._create_project(client, auth_headers)

        create_resp = await client.post(
            f"/api/v1/videos/projects/{project_id}/videos",
            json={"title": "Huge Video"},
            headers=auth_headers,
        )
        video_id = create_resp.json()["id"]

        # Simulate oversized file by using a content check
        big_file = io.BytesIO(b"x" * (501 * 1024 * 1024))  # 501 MB
        response = await client.post(
            f"/api/v1/videos/{video_id}/upload",
            files={"file": ("huge.mp4", big_file, "video/mp4")},
            headers=auth_headers,
        )
        assert response.status_code == 413

    async def test_upload_invalid_type_returns_422(
        self, client: AsyncClient, auth_headers
    ):
        project_id = await self._create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/videos/projects/{project_id}/videos",
            json={"title": "Invalid Type"},
            headers=auth_headers,
        )
        video_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/videos/{video_id}/upload",
            files={"file": ("malware.exe", io.BytesIO(b"bad"), "application/octet-stream")},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_process_video_returns_202(
        self,
        client: AsyncClient,
        auth_headers,
        mock_storage,
        mock_celery_task,
    ):
        project_id = await self._create_project(client, auth_headers)

        # Create and upload
        create_resp = await client.post(
            f"/api/v1/videos/projects/{project_id}/videos",
            json={"title": "Process Me"},
            headers=auth_headers,
        )
        video_id = create_resp.json()["id"]

        fake_video = io.BytesIO(b"video" * 100)
        await client.post(
            f"/api/v1/videos/{video_id}/upload",
            files={"file": ("test.mp4", fake_video, "video/mp4")},
            headers=auth_headers,
        )

        # Process
        response = await client.post(
            f"/api/v1/videos/{video_id}/process",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["video_id"] == video_id
        mock_celery_task.assert_called_once()

    async def test_get_video_status(
        self, client: AsyncClient, auth_headers, mock_storage
    ):
        project_id = await self._create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/videos/projects/{project_id}/videos",
            json={"title": "Status Check"},
            headers=auth_headers,
        )
        video_id = create_resp.json()["id"]

        response = await client.get(
            f"/api/v1/videos/{video_id}/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "id" in data

    async def test_list_videos_in_project(
        self, client: AsyncClient, auth_headers
    ):
        project_id = await self._create_project(client, auth_headers)

        # Create 3 videos
        for i in range(3):
            await client.post(
                f"/api/v1/videos/projects/{project_id}/videos",
                json={"title": f"Video {i}"},
                headers=auth_headers,
            )

        response = await client.get(
            f"/api/v1/videos/projects/{project_id}/videos",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    async def test_delete_video(self, client: AsyncClient, auth_headers, mock_storage):
        project_id = await self._create_project(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/videos/projects/{project_id}/videos",
            json={"title": "Delete Me"},
            headers=auth_headers,
        )
        video_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/videos/{video_id}",
            params={"project_id": project_id},
            headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data