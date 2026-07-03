"""Tests for ScenarioResult password recording."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.testing import Scenario

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.models.user_mixin import UserMixin


class TestScenarioPasswords:
    """Tests for ScenarioResult.passwords recording."""

    def test_build_records_passwords_by_email(self, session: Session, admin_user: UserMixin) -> None:
        """build() records each user's plaintext password keyed by email."""
        result = (
            Scenario().with_user(name="pwuser", password="secretpw123").build(session=session, admin_user=admin_user)
        )
        assert result.passwords["pwuser@test.com"] == "secretpw123"
