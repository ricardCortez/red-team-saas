"""Unit tests for Phase 9 CRUDProject methods"""
import pytest

from app.crud.project import crud_project
from app.crud.project_member import crud_project_member
from app.models.project import Project, ProjectStatus
from app.models.project_member import ProjectMember, ProjectRole
from app.models.user import User, UserRoleEnum
from app.core.security import PasswordHandler


def _make_user(db, email="u@test.com", username="utest", superuser=False) -> User:
    user = User(
        email=email,
        username=username,
        hashed_password=PasswordHandler.hash_password("pass"),
        is_superuser=superuser,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_project(db, owner: User, name="Test Project") -> Project:
    from app.schemas.project import ProjectCreate
    payload = ProjectCreate(name=name, target="10.0.0.1")
    return crud_project.create_with_owner_member(db, obj_in=payload, owner_id=owner.id)


# ── create_with_owner_member ──────────────────────────────────────────────────

class TestCreateWithOwnerMember:
    def test_create_adds_owner_as_lead(self, db_session):
        owner = _make_user(db_session)
        project = _make_project(db_session, owner)

        members = crud_project_member.list_members(db_session, project.id)
        assert len(members) == 1
        assert members[0].user_id == owner.id
        assert members[0].role == ProjectRole.lead

    def test_project_owner_id_set(self, db_session):
        owner = _make_user(db_session, "owner2@test.com", "owner2")
        project = _make_project(db_session, owner)
        assert project.owner_id == owner.id

    def test_project_status_default_active(self, db_session):
        owner = _make_user(db_session, "owner3@test.com", "owner3")
        project = _make_project(db_session, owner)
        assert project.status == ProjectStatus.active


# ── get_for_user ──────────────────────────────────────────────────────────────

class TestGetForUser:
    def test_non_member_sees_no_projects(self, db_session):
        owner  = _make_user(db_session, "ow@t.com", "ow")
        other  = _make_user(db_session, "other@t.com", "other")
        _make_project(db_session, owner)

        items, total = crud_project.get_for_user(db_session, other.id)
        assert total == 0
        assert items == []

    def test_member_sees_their_project(self, db_session):
        owner = _make_user(db_session, "ow2@t.com", "ow2")
        project = _make_project(db_session, owner)

        items, total = crud_project.get_for_user(db_session, owner.id)
        assert total == 1
        assert items[0].id == project.id

    def test_admin_sees_all_projects(self, db_session):
        owner = _make_user(db_session, "ow3@t.com", "ow3")
        admin = _make_user(db_session, "adm@t.com", "adm", superuser=True)
        _make_project(db_session, owner, "Project One")
        _make_project(db_session, owner, "Project Two")

        items, total = crud_project.get_for_user(db_session, admin.id)
        assert total == 2

    def test_filter_by_status(self, db_session):
        owner   = _make_user(db_session, "ow4@t.com", "ow4")
        project = _make_project(db_session, owner)
        crud_project.archive(db_session, project)

        active_items, _ = crud_project.get_for_user(
            db_session, owner.id, status=ProjectStatus.active
        )
        archived_items, _ = crud_project.get_for_user(
            db_session, owner.id, status=ProjectStatus.archived
        )
        assert len(active_items) == 0
        assert len(archived_items) == 1


# ── archive ───────────────────────────────────────────────────────────────────

class TestArchive:
    def test_archive_sets_archived_at(self, db_session):
        owner   = _make_user(db_session, "ow5@t.com", "ow5")
        project = _make_project(db_session, owner)
        result  = crud_project.archive(db_session, project)

        assert result.status == ProjectStatus.archived
        assert result.archived_at is not None

    def test_archive_sets_status(self, db_session):
        owner   = _make_user(db_session, "ow6@t.com", "ow6")
        project = _make_project(db_session, owner)
        crud_project.archive(db_session, project)
        assert project.status == ProjectStatus.archived


# ── can_manage ────────────────────────────────────────────────────────────────

class TestCanManage:
    def test_lead_can_manage(self, db_session):
        owner = _make_user(db_session, "lead@t.com", "lead")
        project = _make_project(db_session, owner)
        assert crud_project.can_manage(db_session, project.id, owner.id) is True

    def test_viewer_cannot_manage(self, db_session):
        owner  = _make_user(db_session, "own7@t.com", "own7")
        viewer = _make_user(db_session, "view@t.com", "view")
        project = _make_project(db_session, owner)
        crud_project_member.add(db_session, project.id, viewer.id, ProjectRole.viewer, owner.id)

        assert crud_project.can_manage(db_session, project.id, viewer.id) is False

    def test_operator_cannot_manage(self, db_session):
        owner    = _make_user(db_session, "own8@t.com", "own8")
        operator = _make_user(db_session, "oper@t.com", "oper")
        project  = _make_project(db_session, owner)
        crud_project_member.add(db_session, project.id, operator.id, ProjectRole.operator, owner.id)

        assert crud_project.can_manage(db_session, project.id, operator.id) is False

    def test_superuser_can_manage_any(self, db_session):
        owner  = _make_user(db_session, "own9@t.com", "own9")
        admin  = _make_user(db_session, "adm2@t.com", "adm2", superuser=True)
        project = _make_project(db_session, owner)

        assert crud_project.can_manage(db_session, project.id, admin.id) is True
