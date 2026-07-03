"""
Custom-user test session: registers a custom user model BEFORE any fixture runs.

This suite runs as a SEPARATE pytest session (see .github/workflows/test.yml):
one kernel per process is a hard constraint, so these tests must never be
collected together with the main suite (which uses DefaultUser). The kwik
fixtures plugin is loaded via `-p kwik.testing.fixtures` on the command line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from kwik.applications import Kwik
from kwik.database import create_session
from kwik.dependencies.session import _get_session
from kwik.kernel import Kernel, UserSchemas
from kwik.models import Base, UserMixin
from kwik.schemas import UserProfile, UserProfileUpdate, UserRegistration
from kwik.testing import IdentityAwareTestClient

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    from kwik.settings import BaseKwikSettings


class CustomTestUser(Base, UserMixin):
    """Custom user model with one extra column, mirroring a consuming application."""

    __tablename__ = "users"

    nickname: Mapped[str] = mapped_column(String, default="", nullable=False)


class CustomUserProfile(UserProfile):
    """Profile schema exposing the custom column."""

    nickname: str


class CustomUserRegistration(UserRegistration):
    """Registration schema accepting the custom column."""

    nickname: str = ""


class CustomUserUpdate(UserProfileUpdate):
    """Update schema accepting the custom column."""

    nickname: str | None = None


KERNEL = Kernel(
    user_model=CustomTestUser,
    schemas=UserSchemas(profile=CustomUserProfile, registration=CustomUserRegistration, update=CustomUserUpdate),
)


@pytest.fixture(scope="session")
def kwik_app(settings: BaseKwikSettings) -> Kwik:
    """Kwik application built from the custom kernel."""
    return Kwik(settings=settings, api_router=KERNEL.create_api_router())


@pytest.fixture
def client(kwik_app: Kwik, engine: Engine) -> Generator[TestClient, None, None]:
    """HTTP client with a rolled-back session per test (mirrors tests/api/conftest.py)."""
    api_session = create_session(engine=engine)

    def _get_session_override() -> Generator[Session, None, None]:
        yield api_session

    kwik_app.app.dependency_overrides[_get_session] = _get_session_override

    with TestClient(app=kwik_app.app) as client:
        yield client

    api_session.rollback()
    api_session.close()


@pytest.fixture
def identity_aware_client(client: TestClient, settings: BaseKwikSettings) -> IdentityAwareTestClient:
    """TestClient with identity-aware authentication context switching."""
    return IdentityAwareTestClient(client, settings)
