"""Unit tests for CRUDTarget (Phase 9)"""
import pytest

from app.crud.target import crud_target
from app.crud.project import crud_project
from app.models.target import Target, TargetType, TargetStatus
from app.models.user import User
from app.core.security import PasswordHandler
from app.schemas.target import TargetCreate, TargetUpdate
from app.schemas.project import ProjectCreate


def _make_user(db, email="u@t.com", username="u") -> User:
    user = User(
        email=email,
        username=username,
        hashed_password=PasswordHandler.hash_password("pass"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_project(db, owner):
    return crud_project.create_with_owner_member(
        db, obj_in=ProjectCreate(name="T Project", target="10.0.0.0/24"), owner_id=owner.id
    )


class TestCreateTarget:
    def test_create_target(self, db_session):
        owner   = _make_user(db_session)
        project = _make_project(db_session, owner)

        payload = TargetCreate(value="10.0.0.1", target_type=TargetType.ip)
        target  = crud_target.create(db_session, project.id, owner.id, payload)

        assert target.id is not None
        assert target.value == "10.0.0.1"
        assert target.target_type == TargetType.ip
        assert target.status == TargetStatus.in_scope
        assert target.project_id == project.id

    def test_create_target_out_of_scope(self, db_session):
        owner   = _make_user(db_session, "u2@t.com", "u2")
        project = _make_project(db_session, owner)

        payload = TargetCreate(
            value="10.0.1.0/24",
            target_type=TargetType.cidr,
            status=TargetStatus.out_of_scope,
        )
        target = crud_target.create(db_session, project.id, owner.id, payload)
        assert target.status == TargetStatus.out_of_scope


class TestBulkCreate:
    def test_bulk_create_targets(self, db_session):
        owner   = _make_user(db_session, "u3@t.com", "u3")
        project = _make_project(db_session, owner)

        payloads = [
            TargetCreate(value="host1.example.com", target_type=TargetType.hostname),
            TargetCreate(value="host2.example.com", target_type=TargetType.hostname),
            TargetCreate(value="10.1.0.0/16", target_type=TargetType.cidr),
        ]
        created = crud_target.bulk_create(db_session, project.id, owner.id, payloads)
        assert len(created) == 3
        values = {t.value for t in created}
        assert "host1.example.com" in values
        assert "10.1.0.0/16" in values


class TestGetByProject:
    def test_get_all_targets(self, db_session):
        owner   = _make_user(db_session, "u4@t.com", "u4")
        project = _make_project(db_session, owner)

        for i in range(3):
            crud_target.create(
                db_session, project.id, owner.id,
                TargetCreate(value=f"10.0.0.{i+1}", target_type=TargetType.ip),
            )

        items, total = crud_target.get_by_project(db_session, project.id)
        assert total == 3
        assert len(items) == 3

    def test_filter_by_status(self, db_session):
        owner   = _make_user(db_session, "u5@t.com", "u5")
        project = _make_project(db_session, owner)

        crud_target.create(
            db_session, project.id, owner.id,
            TargetCreate(value="10.0.0.1", target_type=TargetType.ip),
        )
        crud_target.create(
            db_session, project.id, owner.id,
            TargetCreate(
                value="10.0.0.2", target_type=TargetType.ip,
                status=TargetStatus.out_of_scope,
            ),
        )

        in_scope, _ = crud_target.get_by_project(
            db_session, project.id, status=TargetStatus.in_scope
        )
        out_scope, _ = crud_target.get_by_project(
            db_session, project.id, status=TargetStatus.out_of_scope
        )
        assert len(in_scope) == 1
        assert len(out_scope) == 1


class TestUpdateTarget:
    def test_update_target_status(self, db_session):
        owner   = _make_user(db_session, "u6@t.com", "u6")
        project = _make_project(db_session, owner)

        target = crud_target.create(
            db_session, project.id, owner.id,
            TargetCreate(value="10.0.0.5", target_type=TargetType.ip),
        )
        updated = crud_target.update(
            db_session, target, TargetUpdate(status=TargetStatus.out_of_scope)
        )
        assert updated.status == TargetStatus.out_of_scope

    def test_update_target_metadata(self, db_session):
        owner   = _make_user(db_session, "u7@t.com", "u7")
        project = _make_project(db_session, owner)

        target = crud_target.create(
            db_session, project.id, owner.id,
            TargetCreate(value="10.0.0.6", target_type=TargetType.ip),
        )
        updated = crud_target.update(
            db_session, target,
            TargetUpdate(os_hint="Linux", tech_stack="nginx,python"),
        )
        assert updated.os_hint == "Linux"
        assert updated.tech_stack == "nginx,python"
