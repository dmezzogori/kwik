"""Tests for Kwik application class and seeding functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kwik.api.api import api_router
from kwik.applications import Kwik
from kwik.crud import Context, crud_users
from kwik.database import create_session, session_scope
from kwik.schemas import UserRegistration

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from kwik.settings import BaseKwikSettings


class TestKwikApplicationCreation:
    """Test basic Kwik application creation with and without seeding."""

    def test_kwik_creation_without_seed_db(self, settings: BaseKwikSettings) -> None:
        """Test that Kwik can be created without seed_db parameter (default None)."""
        kwik_app = Kwik(settings=settings, api_router=api_router)

        assert kwik_app is not None
        assert kwik_app.settings == settings
        assert kwik_app.app is not None
        assert kwik_app.app.title == settings.PROJECT_NAME

    def test_kwik_creation_with_seed_db(self, settings: BaseKwikSettings) -> None:
        """Test that Kwik can be created with a seed_db callable."""
        mock_seed_db = MagicMock()

        kwik_app = Kwik(settings=settings, api_router=api_router, seed_db=mock_seed_db)

        assert kwik_app is not None
        assert kwik_app.settings == settings
        assert kwik_app.app is not None


class TestSeedingFunctionality:
    """Test database seeding functionality during application lifecycle."""

    def test_seed_db_called_during_startup(self, settings: BaseKwikSettings) -> None:
        """Test that seed_db function is called during application startup."""
        mock_seed_db = MagicMock()

        kwik_app = Kwik(settings=settings, api_router=api_router, seed_db=mock_seed_db)

        with TestClient(app=kwik_app.app):
            pass

        mock_seed_db.assert_called_once()

    def test_seed_db_receives_correct_parameters(self, settings: BaseKwikSettings) -> None:
        """Test that seed_db function receives session and settings as parameters."""
        mock_seed_db = MagicMock()

        kwik_app = Kwik(settings=settings, api_router=api_router, seed_db=mock_seed_db)

        with TestClient(app=kwik_app.app):
            pass

        mock_seed_db.assert_called_once()
        call_args = mock_seed_db.call_args

        expected_arg_count = 2
        assert len(call_args[0]) == expected_arg_count
        session, passed_settings = call_args[0]
        assert isinstance(session, Session)
        assert passed_settings == settings

    def test_seed_db_called_once_only(self, settings: BaseKwikSettings) -> None:
        """Test that seed_db is called exactly once during application lifecycle."""
        mock_seed_db = MagicMock()

        kwik_app = Kwik(settings=settings, api_router=api_router, seed_db=mock_seed_db)

        with TestClient(app=kwik_app.app) as client:
            client.get("/api/v1/context/")
            client.get("/api/v1/context/")

        mock_seed_db.assert_called_once()

    def test_no_seeding_when_seed_db_is_none(self, settings: BaseKwikSettings) -> None:
        """Test that no seeding occurs when seed_db is None."""
        kwik_app = Kwik(settings=settings, api_router=api_router, seed_db=None)

        with TestClient(app=kwik_app.app):
            pass

        assert kwik_app._seed_db is None


class TestSeedingBehavior:
    """Test seeding behavior with actual database operations."""

    def test_seed_db_session_functional(self, settings: BaseKwikSettings) -> None:
        """Test that the session passed to seed_db can perform database operations."""
        created_user_data = None

        def seed_function(session: Session, _settings: BaseKwikSettings) -> None:
            nonlocal created_user_data
            context = Context(session=session, user=None)
            user = crud_users.create(
                obj_in=UserRegistration(
                    name="Test",
                    surname="Seed",
                    email="seed@example.com",
                    password="testpassword123",
                ),
                context=context,
            )
            created_user_data = {
                "id": user.id,
                "name": user.name,
                "surname": user.surname,
                "email": user.email,
            }

        kwik_app = Kwik(settings=settings, api_router=api_router, seed_db=seed_function)

        with TestClient(app=kwik_app.app):
            pass

        assert created_user_data is not None
        assert created_user_data["name"] == "Test"
        assert created_user_data["surname"] == "Seed"
        assert created_user_data["email"] == "seed@example.com"

    def test_seeded_data_persists(self, settings: BaseKwikSettings, engine: Engine) -> None:
        """Test that data created by seed function persists after application startup."""
        test_email = "persistent@example.com"

        def seed_function(session: Session, _settings: BaseKwikSettings) -> None:
            context = Context(session=session, user=None)
            crud_users.create(
                obj_in=UserRegistration(
                    name="Persistent",
                    surname="User",
                    email=test_email,
                    password="persistentpassword123",
                ),
                context=context,
            )

        kwik_app = Kwik(settings=settings, api_router=api_router, seed_db=seed_function)

        with TestClient(app=kwik_app.app):
            pass

        _session = create_session(engine=engine)
        with session_scope(session=_session) as scoped_session:
            context = Context(session=scoped_session, user=None)
            user = crud_users.get_by_email(email=test_email, context=context)

            assert user is not None
            assert user.email == test_email
            assert user.name == "Persistent"
            assert user.surname == "User"


class TestSeedingErrorHandling:
    """Test error handling in seeding functionality."""

    def test_seed_db_error_handling(self, settings: BaseKwikSettings) -> None:
        """Test that errors in seed function don't crash the application."""

        def failing_seed_function(_session: Session, _settings: BaseKwikSettings) -> None:
            error_message = "Intentional seeding error"
            raise ValueError(error_message)

        kwik_app = Kwik(settings=settings, api_router=api_router, seed_db=failing_seed_function)

        with (
            pytest.raises(ValueError, match="Intentional seeding error"),
            TestClient(app=kwik_app.app),
        ):
            pass

    def test_seed_db_transaction_rollback(self, settings: BaseKwikSettings, engine: Engine) -> None:
        """Test that database changes are rolled back when seed function fails."""
        test_email = "rollback@example.com"

        def failing_seed_function(session: Session, _settings: BaseKwikSettings) -> None:
            context = Context(session=session, user=None)
            crud_users.create(
                obj_in=UserRegistration(
                    name="Rollback",
                    surname="User",
                    email=test_email,
                    password="rollbackpassword123",
                ),
                context=context,
            )
            error_message = "Intentional failure after user creation"
            raise RuntimeError(error_message)

        kwik_app = Kwik(settings=settings, api_router=api_router, seed_db=failing_seed_function)

        with (
            pytest.raises(RuntimeError, match="Intentional failure after user creation"),
            TestClient(app=kwik_app.app),
        ):
            pass

        _session = create_session(engine=engine)
        with session_scope(session=_session) as scoped_session:
            context = Context(session=scoped_session, user=None)
            user = crud_users.get_by_email(email=test_email, context=context)

            assert user is None
