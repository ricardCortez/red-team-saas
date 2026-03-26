"""Integration tests – Phase 9: Projects, Members, Targets, Scope"""
import pytest
from tests.conftest import TestingSessionLocal
from app.models.user import User, UserRoleEnum
from app.core.security import PasswordHandler, JWTHandler


# ── helpers ───────────────────────────────────────────────────────────────────

def _register_login(client, email: str, username: str, password="Pass123!"):
    """Register a user and return (token, user_id)."""
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password,
              "full_name": "QA User"},
    )
    assert reg.status_code == 201, reg.text
    user_id = reg.json()["id"]
    resp = client.post(
        "/api/v1/auth/login",
        params={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"], user_id


def _admin_token_uid():
    db = TestingSessionLocal()
    try:
        user = User(
            email="admin9@qa.test",
            username="admin9",
            hashed_password=PasswordHandler.hash_password("Admin123!"),
            is_superuser=True,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = JWTHandler.create_access_token({"sub": str(user.id), "email": user.email})
        return token, user.id
    finally:
        db.close()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


PROJECT_DATA = {
    "name": "Phase9 Project",
    "target": "192.168.1.0/24",
    "scope": "internal",
}


def _create_project(client, token: str, data: dict = None) -> dict:
    resp = client.post("/api/v1/projects/", json=data or PROJECT_DATA, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Project CRUD ──────────────────────────────────────────────────────────────

class TestCreateProject:
    def test_create_project(self, client):
        token, _ = _register_login(client, "p9a@t.com", "p9a")
        p = _create_project(client, token)
        assert p["name"] == "Phase9 Project"
        assert p["status"] == "active"

    def test_create_project_owner_added_as_lead(self, client):
        token, _ = _register_login(client, "p9b@t.com", "p9b")
        p = _create_project(client, token)
        resp = client.get(f"/api/v1/projects/{p['id']}/members", headers=_auth(token))
        assert resp.status_code == 200
        members = resp.json()
        assert len(members) == 1
        assert members[0]["role"] == "lead"

    def test_create_project_with_rules_of_engagement(self, client):
        token, _ = _register_login(client, "p9c@t.com", "p9c")
        resp = client.post(
            "/api/v1/projects/",
            json={**PROJECT_DATA, "rules_of_engagement": "No DOS attacks"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        assert resp.json()["rules_of_engagement"] == "No DOS attacks"


class TestListProjects:
    def test_list_projects_member_only(self, client):
        tok_a, _ = _register_login(client, "la@t.com", "la")
        tok_b, _ = _register_login(client, "lb@t.com", "lb")
        _create_project(client, tok_a)
        _create_project(client, tok_b, {**PROJECT_DATA, "name": "B Project"})

        resp_a = client.get("/api/v1/projects/", headers=_auth(tok_a))
        assert resp_a.status_code == 200
        names_a = [p["name"] for p in resp_a.json()["items"]]
        assert "Phase9 Project" in names_a
        assert "B Project" not in names_a

    def test_admin_sees_all_projects(self, client):
        tok_a, _   = _register_login(client, "la2@t.com", "la2")
        admin, _   = _admin_token_uid()
        _create_project(client, tok_a)
        _create_project(client, tok_a, {**PROJECT_DATA, "name": "Second Project"})

        resp = client.get("/api/v1/projects/", headers=_auth(admin))
        assert resp.json()["total"] >= 2


class TestGetProject:
    def test_get_project_detail_with_counts(self, client):
        token, _ = _register_login(client, "gp@t.com", "gp")
        p = _create_project(client, token)
        resp = client.get(f"/api/v1/projects/{p['id']}", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "member_count" in data
        assert data["member_count"] >= 1
        assert "target_count" in data

    def test_non_member_cannot_get_project(self, client):
        tok_owner, _ = _register_login(client, "own@t.com", "own")
        tok_other, _ = _register_login(client, "oth@t.com", "oth")
        p = _create_project(client, tok_owner)

        resp = client.get(f"/api/v1/projects/{p['id']}", headers=_auth(tok_other))
        assert resp.status_code == 403


class TestUpdateProject:
    def test_patch_project_by_lead(self, client):
        token, _ = _register_login(client, "upd@t.com", "upd")
        p = _create_project(client, token)
        resp = client.patch(
            f"/api/v1/projects/{p['id']}",
            json={"client_name": "ACME Corp"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["client_name"] == "ACME Corp"

    def test_viewer_cannot_update_project(self, client):
        tok_owner,  _        = _register_login(client, "own2@t.com", "own2")
        tok_viewer, view_uid = _register_login(client, "vw@t.com",   "vw")
        p = _create_project(client, tok_owner)

        client.post(
            f"/api/v1/projects/{p['id']}/members",
            json={"user_id": view_uid, "role": "viewer"},
            headers=_auth(tok_owner),
        )

        resp = client.patch(
            f"/api/v1/projects/{p['id']}",
            json={"client_name": "Hacked"},
            headers=_auth(tok_viewer),
        )
        assert resp.status_code == 403


class TestArchiveProject:
    def test_archive_project(self, client):
        token, _ = _register_login(client, "arc@t.com", "arc")
        p = _create_project(client, token)
        resp = client.post(f"/api/v1/projects/{p['id']}/archive", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    def test_archive_already_archived(self, client):
        token, _ = _register_login(client, "arc2@t.com", "arc2")
        p = _create_project(client, token)
        client.post(f"/api/v1/projects/{p['id']}/archive", headers=_auth(token))
        resp = client.post(f"/api/v1/projects/{p['id']}/archive", headers=_auth(token))
        assert resp.status_code == 400

    def test_non_lead_cannot_archive(self, client):
        tok_owner,  _        = _register_login(client, "arc3@t.com", "arc3")
        tok_viewer, view_uid = _register_login(client, "arc4@t.com", "arc4")
        p = _create_project(client, tok_owner)

        client.post(
            f"/api/v1/projects/{p['id']}/members",
            json={"user_id": view_uid, "role": "viewer"},
            headers=_auth(tok_owner),
        )

        resp = client.post(f"/api/v1/projects/{p['id']}/archive", headers=_auth(tok_viewer))
        assert resp.status_code == 403


# ── Members ───────────────────────────────────────────────────────────────────

class TestMembers:
    def test_add_member(self, client):
        tok_owner, _       = _register_login(client, "mb1@t.com", "mb1")
        tok_new,   new_uid = _register_login(client, "mb2@t.com", "mb2")
        p = _create_project(client, tok_owner)

        resp = client.post(
            f"/api/v1/projects/{p['id']}/members",
            json={"user_id": new_uid, "role": "operator"},
            headers=_auth(tok_owner),
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "operator"

    def test_list_members(self, client):
        tok_owner, _       = _register_login(client, "mb3@t.com", "mb3")
        tok_new,   new_uid = _register_login(client, "mb4@t.com", "mb4")
        p = _create_project(client, tok_owner)

        client.post(
            f"/api/v1/projects/{p['id']}/members",
            json={"user_id": new_uid, "role": "viewer"},
            headers=_auth(tok_owner),
        )

        resp = client.get(f"/api/v1/projects/{p['id']}/members", headers=_auth(tok_owner))
        assert resp.status_code == 200
        assert len(resp.json()) == 2  # owner + new member

    def test_remove_member(self, client):
        tok_owner, owner_uid = _register_login(client, "mb5@t.com", "mb5")
        tok_new,   new_uid   = _register_login(client, "mb6@t.com", "mb6")
        p = _create_project(client, tok_owner)

        client.post(
            f"/api/v1/projects/{p['id']}/members",
            json={"user_id": new_uid, "role": "viewer"},
            headers=_auth(tok_owner),
        )

        resp = client.delete(
            f"/api/v1/projects/{p['id']}/members/{new_uid}",
            headers=_auth(tok_owner),
        )
        assert resp.status_code == 204

    def test_remove_member_cannot_remove_owner(self, client):
        tok_owner, owner_uid = _register_login(client, "mb7@t.com", "mb7")
        p = _create_project(client, tok_owner)

        resp = client.delete(
            f"/api/v1/projects/{p['id']}/members/{owner_uid}",
            headers=_auth(tok_owner),
        )
        assert resp.status_code == 400


# ── Targets ───────────────────────────────────────────────────────────────────

class TestTargets:
    def test_add_target(self, client):
        token, _ = _register_login(client, "tgt1@t.com", "tgt1")
        p = _create_project(client, token)

        resp = client.post(
            f"/api/v1/projects/{p['id']}/targets",
            json={"value": "10.0.0.1", "target_type": "ip"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        assert resp.json()["value"] == "10.0.0.1"

    def test_list_targets(self, client):
        token, _ = _register_login(client, "tgt2@t.com", "tgt2")
        p = _create_project(client, token)

        for i in range(3):
            client.post(
                f"/api/v1/projects/{p['id']}/targets",
                json={"value": f"10.0.0.{i+1}", "target_type": "ip"},
                headers=_auth(token),
            )

        resp = client.get(f"/api/v1/projects/{p['id']}/targets", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["total"] == 3

    def test_bulk_add_targets(self, client):
        token, _ = _register_login(client, "tgt3@t.com", "tgt3")
        p = _create_project(client, token)

        resp = client.post(
            f"/api/v1/projects/{p['id']}/targets/bulk",
            json={
                "targets": [
                    {"value": "10.1.0.1", "target_type": "ip"},
                    {"value": "10.1.0.2", "target_type": "ip"},
                    {"value": "*.example.com", "target_type": "hostname"},
                ]
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        assert len(resp.json()) == 3

    def test_update_target(self, client):
        token, _ = _register_login(client, "tgt4@t.com", "tgt4")
        p = _create_project(client, token)

        tgt = client.post(
            f"/api/v1/projects/{p['id']}/targets",
            json={"value": "10.0.0.5", "target_type": "ip"},
            headers=_auth(token),
        ).json()

        resp = client.patch(
            f"/api/v1/projects/{p['id']}/targets/{tgt['id']}",
            json={"status": "out_of_scope", "os_hint": "Windows"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "out_of_scope"
        assert resp.json()["os_hint"] == "Windows"

    def test_delete_target(self, client):
        token, _ = _register_login(client, "tgt5@t.com", "tgt5")
        p = _create_project(client, token)

        tgt = client.post(
            f"/api/v1/projects/{p['id']}/targets",
            json={"value": "10.0.0.9", "target_type": "ip"},
            headers=_auth(token),
        ).json()

        resp = client.delete(
            f"/api/v1/projects/{p['id']}/targets/{tgt['id']}",
            headers=_auth(token),
        )
        assert resp.status_code == 204


# ── Scope validation ──────────────────────────────────────────────────────────

class TestScopeValidation:
    def test_validate_scope_in_scope(self, client):
        token, _ = _register_login(client, "sv1@t.com", "sv1")
        p = _create_project(client, token)

        client.post(
            f"/api/v1/projects/{p['id']}/targets",
            json={"value": "10.0.0.0/24", "target_type": "cidr"},
            headers=_auth(token),
        )

        resp = client.post(
            f"/api/v1/projects/{p['id']}/targets/validate",
            params={"target": "10.0.0.50"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["in_scope"] is True

    def test_validate_scope_out_of_scope(self, client):
        token, _ = _register_login(client, "sv2@t.com", "sv2")
        p = _create_project(client, token)

        client.post(
            f"/api/v1/projects/{p['id']}/targets",
            json={"value": "10.0.0.0/24", "target_type": "cidr"},
            headers=_auth(token),
        )

        resp = client.post(
            f"/api/v1/projects/{p['id']}/targets/validate",
            params={"target": "172.16.0.1"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.json()["in_scope"] is False

    def test_execution_blocked_out_of_scope(self, client):
        """POST /executions with a target outside project scope returns 403."""
        token, _ = _register_login(client, "sv3@t.com", "sv3")
        p = _create_project(client, token)

        client.post(
            f"/api/v1/projects/{p['id']}/targets",
            json={"value": "10.0.0.0/24", "target_type": "cidr"},
            headers=_auth(token),
        )

        resp = client.post(
            "/api/v1/executions",
            json={
                "tool_name": "nmap",
                "target": "192.168.99.1",   # outside scope
                "project_id": p["id"],
            },
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_execution_allowed_in_scope(self, client):
        """POST /executions with an in-scope target is accepted (202 or 400 if tool unknown)."""
        token, _ = _register_login(client, "sv4@t.com", "sv4")
        p = _create_project(client, token)

        client.post(
            f"/api/v1/projects/{p['id']}/targets",
            json={"value": "10.0.0.0/24", "target_type": "cidr"},
            headers=_auth(token),
        )

        resp = client.post(
            "/api/v1/executions",
            json={
                "tool_name": "nmap",
                "target": "10.0.0.5",
                "project_id": p["id"],
            },
            headers=_auth(token),
        )
        # 202 Accepted OR 400 if nmap not registered in test env
        assert resp.status_code in (202, 400)


# ── Stats & Activity ──────────────────────────────────────────────────────────

class TestStatsAndActivity:
    def test_project_stats_endpoint(self, client):
        token, _ = _register_login(client, "st1@t.com", "st1")
        p = _create_project(client, token)

        resp = client.get(f"/api/v1/projects/{p['id']}/stats", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data or "scan_count" in data

    def test_project_activity_log(self, client):
        token, _ = _register_login(client, "al1@t.com", "al1")
        p = _create_project(client, token)

        # Archive generates an audit log entry
        client.post(f"/api/v1/projects/{p['id']}/archive", headers=_auth(token))

        resp = client.get(f"/api/v1/projects/{p['id']}/activity", headers=_auth(token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
