"""Tests for current user context variable."""

from __future__ import annotations

import asyncio
import contextlib
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from kwik.database.context_vars.current_user import current_user_ctx_var


@pytest.mark.usefixtures("clean_context_vars")
class TestCurrentUserContextVar:
    """Test suite for current_user_ctx_var context variable."""

    def test_default_value_is_none(self) -> None:
        """Test that the default value of current_user_ctx_var is None."""
        assert current_user_ctx_var.get() is None

    def test_set_and_get_user(self, mock_user: MagicMock) -> None:
        """Test setting and getting a User object."""
        token = current_user_ctx_var.set(mock_user)

        try:
            retrieved_user = current_user_ctx_var.get()
            assert retrieved_user is mock_user
            assert retrieved_user.id == 123
            assert retrieved_user.email == "test@example.com"
        finally:
            current_user_ctx_var.reset(token)

    def test_token_management(self, mock_user: MagicMock) -> None:
        """Test proper token-based context management."""
        # Initial state
        assert current_user_ctx_var.get() is None

        # Set first user
        token1 = current_user_ctx_var.set(mock_user)
        assert current_user_ctx_var.get() is mock_user

        # Set second user (nested)
        different_user = MagicMock()
        different_user.id = 456
        different_user.email = "different@example.com"
        token2 = current_user_ctx_var.set(different_user)
        assert current_user_ctx_var.get() is different_user

        # Reset to first user
        current_user_ctx_var.reset(token2)
        assert current_user_ctx_var.get() is mock_user

        # Reset to original state
        current_user_ctx_var.reset(token1)
        assert current_user_ctx_var.get() is None

    def test_context_isolation_between_threads(self, mock_user: MagicMock) -> None:
        """Test that context variables are isolated between threads."""
        results = {}

        def thread1_work() -> None:
            # Thread 1 sets its own user
            thread1_user = MagicMock()
            thread1_user.id = 111
            thread1_user.email = "thread1@example.com"
            token = current_user_ctx_var.set(thread1_user)
            try:
                results["thread1"] = current_user_ctx_var.get()
            finally:
                current_user_ctx_var.reset(token)

        def thread2_work() -> None:
            # Thread 2 should not see thread 1's user
            results["thread2"] = current_user_ctx_var.get()

            # Thread 2 sets its own user
            thread2_user = MagicMock()
            thread2_user.id = 222
            thread2_user.email = "thread2@example.com"
            token = current_user_ctx_var.set(thread2_user)
            try:
                results["thread2_with_user"] = current_user_ctx_var.get()
            finally:
                current_user_ctx_var.reset(token)

        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(thread1_work)
            future2 = executor.submit(thread2_work)

            future1.result()
            future2.result()

        # Each thread should have its own isolated context
        assert results["thread2"] is None  # Thread 2 didn't see thread 1's user
        assert results["thread1"] is not None
        assert results["thread2_with_user"] is not None
        assert results["thread1"].id == 111
        assert results["thread2_with_user"].id == 222
        assert results["thread1"] is not results["thread2_with_user"]

    @pytest.mark.asyncio
    async def test_async_context_isolation(self, mock_user: MagicMock) -> None:
        """Test that context variables work correctly in async contexts."""
        results = {}

        async def task1() -> None:
            # Task 1 sets its own user
            task1_user = MagicMock()
            task1_user.id = 333
            task1_user.email = "task1@example.com"
            token = current_user_ctx_var.set(task1_user)
            try:
                # Yield control to allow task2 to run
                await asyncio.sleep(0.01)
                results["task1"] = current_user_ctx_var.get()
            finally:
                current_user_ctx_var.reset(token)

        async def task2() -> None:
            # Task 2 should not see task 1's user
            results["task2_initial"] = current_user_ctx_var.get()

            # Task 2 sets its own user
            task2_user = MagicMock()
            task2_user.id = 444
            task2_user.email = "task2@example.com"
            token = current_user_ctx_var.set(task2_user)
            try:
                # Yield control
                await asyncio.sleep(0.01)
                results["task2"] = current_user_ctx_var.get()
            finally:
                current_user_ctx_var.reset(token)

        # Run tasks concurrently
        await asyncio.gather(task1(), task2())

        # Each task should have its own isolated context
        assert results["task2_initial"] is None  # Task 2 didn't see task 1's user
        assert results["task1"] is not None
        assert results["task2"] is not None
        assert results["task1"].id == 333
        assert results["task2"].id == 444
        assert results["task1"] is not results["task2"]

    def test_none_value_handling(self, mock_user: MagicMock) -> None:
        """Test that None can be explicitly set and retrieved."""
        # Set a user first
        token1 = current_user_ctx_var.set(mock_user)
        assert current_user_ctx_var.get() is mock_user

        # Explicitly set None
        token2 = current_user_ctx_var.set(None)
        assert current_user_ctx_var.get() is None

        # Reset should restore previous value
        current_user_ctx_var.reset(token2)
        assert current_user_ctx_var.get() is mock_user

        # Final cleanup
        current_user_ctx_var.reset(token1)
        assert current_user_ctx_var.get() is None

    def test_nested_contexts_with_same_user(self, mock_user: MagicMock) -> None:
        """Test nested contexts with the same user."""
        # Set same user twice (nested)
        token1 = current_user_ctx_var.set(mock_user)
        token2 = current_user_ctx_var.set(mock_user)  # Same user

        assert current_user_ctx_var.get() is mock_user

        # Reset inner context
        current_user_ctx_var.reset(token2)
        assert current_user_ctx_var.get() is mock_user  # Should still be the same user

        # Reset outer context
        current_user_ctx_var.reset(token1)
        assert current_user_ctx_var.get() is None

    @pytest.mark.asyncio
    async def test_context_inheritance_in_tasks(self, mock_user: MagicMock) -> None:
        """Test that child tasks inherit parent context but can override it."""
        results = {}

        # Parent sets context
        token = current_user_ctx_var.set(mock_user)

        try:

            async def child_task() -> None:
                # Child should inherit parent's context
                results["inherited"] = current_user_ctx_var.get()

                # Child can override with its own context
                child_user = MagicMock()
                child_user.id = 999
                child_user.email = "child@example.com"
                child_token = current_user_ctx_var.set(child_user)
                try:
                    results["child_override"] = current_user_ctx_var.get()
                finally:
                    current_user_ctx_var.reset(child_token)

                # After reset, should see parent's context again
                results["after_reset"] = current_user_ctx_var.get()

            await child_task()

            # Parent context should still be active
            results["parent_final"] = current_user_ctx_var.get()

        finally:
            current_user_ctx_var.reset(token)

        # Verify context inheritance and isolation
        assert results["inherited"] is mock_user
        assert results["child_override"].id == 999
        assert results["child_override"] is not mock_user
        assert results["after_reset"] is mock_user
        assert results["parent_final"] is mock_user

    def test_invalid_token_reset_raises_runtime_error(self, mock_user: MagicMock) -> None:
        """Test that resetting with invalid token raises RuntimeError."""
        token = current_user_ctx_var.set(mock_user)

        # Reset once (valid)
        current_user_ctx_var.reset(token)

        # Reset again with same token (invalid)
        with pytest.raises(RuntimeError):
            current_user_ctx_var.reset(token)

    def test_context_var_name_and_default(self) -> None:
        """Test context variable has correct name and default."""
        assert current_user_ctx_var.name == "current_user_ctx_var"
        assert current_user_ctx_var.get("test_default") is None
        assert current_user_ctx_var.get() is None

    def test_user_object_attributes_persistence(self) -> None:
        """Test that user object attributes are preserved in context."""
        # Create a user with specific attributes
        user = MagicMock()
        user.id = 12345
        user.email = "persistent@example.com"
        user.name = "Persistent User"
        user.is_active = True
        user.roles = ["admin", "user"]

        token = current_user_ctx_var.set(user)

        try:
            retrieved_user = current_user_ctx_var.get()
            assert retrieved_user.id == 12345
            assert retrieved_user.email == "persistent@example.com"
            assert retrieved_user.name == "Persistent User"
            assert retrieved_user.is_active is True
            assert retrieved_user.roles == ["admin", "user"]
        finally:
            current_user_ctx_var.reset(token)

    def test_multiple_user_switches_in_sequence(self) -> None:
        """Test switching between different users in sequence."""
        users = []
        tokens = []

        # Create multiple users
        for i in range(5):
            user = MagicMock()
            user.id = i + 1000
            user.email = f"user{i}@example.com"
            users.append(user)

        try:
            # Set users in sequence (nested contexts)
            for user in users:
                token = current_user_ctx_var.set(user)
                tokens.append(token)
                assert current_user_ctx_var.get() is user

            # Reset in reverse order (LIFO)
            for i in range(len(tokens) - 1, -1, -1):
                current_user_ctx_var.reset(tokens[i])
                if i > 0:
                    # Should see previous user
                    assert current_user_ctx_var.get() is users[i - 1]
                else:
                    # Should be None after all are reset
                    assert current_user_ctx_var.get() is None

        finally:
            # Emergency cleanup in case test fails
            for token in reversed(tokens):
                with contextlib.suppress(RuntimeError):
                    current_user_ctx_var.reset(token)  # Token might already be reset

    def test_context_var_with_real_user_like_object(self) -> None:
        """Test with an object that more closely resembles a real User model."""

        # Create an object that looks more like a real User model
        class MockUserModel:
            def __init__(self, user_id, email, name) -> None:
                self.id = user_id
                self.email = email
                self.name = name
                self.is_active = True
                self.created_at = "2023-01-01"

            def __repr__(self) -> str:
                return f"User(id={self.id}, email='{self.email}')"

        user = MockUserModel(user_id=42, email="real@example.com", name="Real User")
        token = current_user_ctx_var.set(user)

        try:
            retrieved_user = current_user_ctx_var.get()
            assert isinstance(retrieved_user, MockUserModel)
            assert retrieved_user.id == 42
            assert retrieved_user.email == "real@example.com"
            assert retrieved_user.name == "Real User"
            assert retrieved_user.is_active is True
            assert str(retrieved_user) == "User(id=42, email='real@example.com')"
        finally:
            current_user_ctx_var.reset(token)
