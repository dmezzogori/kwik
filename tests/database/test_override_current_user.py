"""Tests for current user context manager override."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from kwik.database.context_vars.current_user import current_user_ctx_var
from kwik.database.override_current_user import override_current_user

if TYPE_CHECKING:
    from kwik.models import User


class TestOverrideCurrentUser:
    """Test suite for override_current_user context manager."""

    def test_basic_context_manager_functionality(
        self,
        clean_context_vars,
        mock_user: User,
    ) -> None:
        """Test basic context manager enter/exit functionality."""
        # Initially no user
        assert current_user_ctx_var.get() is None

        # Use context manager
        with override_current_user(mock_user):
            # Within context, user should be set
            assert current_user_ctx_var.get() is mock_user

        # After context, user should be cleared
        assert current_user_ctx_var.get() is None

    def test_context_manager_with_exception(
        self,
        clean_context_vars,
        mock_user: User,
    ) -> None:
        """Test that cleanup happens even when exception is raised."""
        # Initially no user
        assert current_user_ctx_var.get() is None

        # Use context manager with exception
        with pytest.raises(ValueError, match="Test exception"), override_current_user(mock_user):
            # Within context, user should be set
            assert current_user_ctx_var.get() is mock_user

            # Raise exception
            msg = "Test exception"
            raise ValueError(msg)

        # After context (even with exception), user should be cleared
        assert current_user_ctx_var.get() is None

    def test_nested_context_managers(
        self,
        clean_context_vars,
        mock_user: User,
    ) -> None:
        """Test nested context managers with different users."""
        # Create different users
        user1 = mock_user
        user2 = MagicMock()
        user2.id = 456
        user2.email = "user2@example.com"

        user3 = MagicMock()
        user3.id = 789
        user3.email = "user3@example.com"

        # Initially no user
        assert current_user_ctx_var.get() is None

        with override_current_user(user1):
            assert current_user_ctx_var.get() is user1

            with override_current_user(user2):
                assert current_user_ctx_var.get() is user2

                with override_current_user(user3):
                    assert current_user_ctx_var.get() is user3

                # Back to user2
                assert current_user_ctx_var.get() is user2

            # Back to user1
            assert current_user_ctx_var.get() is user1

        # Back to None
        assert current_user_ctx_var.get() is None

    def test_nested_context_managers_with_exception(
        self,
        clean_context_vars,
        mock_user: User,
    ) -> None:
        """Test nested context managers with exception in inner context."""
        # Create different users
        user1 = mock_user
        user2 = MagicMock()
        user2.id = 456
        user2.email = "user2@example.com"

        # Initially no user
        assert current_user_ctx_var.get() is None

        with override_current_user(user1):
            assert current_user_ctx_var.get() is user1

            with pytest.raises(RuntimeError, match="Inner exception"), override_current_user(user2):
                assert current_user_ctx_var.get() is user2

                # Exception in inner context
                msg = "Inner exception"
                raise RuntimeError(msg)

            # Should restore to user1 after inner exception
            assert current_user_ctx_var.get() is user1

        # Should restore to None after outer context
        assert current_user_ctx_var.get() is None

    def test_same_user_nested_context(
        self,
        clean_context_vars,
        mock_user: User,
    ) -> None:
        """Test nested context managers with the same user."""
        # Initially no user
        assert current_user_ctx_var.get() is None

        with override_current_user(mock_user):
            assert current_user_ctx_var.get() is mock_user

            # Nested with same user
            with override_current_user(mock_user):
                assert current_user_ctx_var.get() is mock_user

            # Should still be the same user
            assert current_user_ctx_var.get() is mock_user

        # Should be None after all contexts
        assert current_user_ctx_var.get() is None

    def test_context_manager_with_none_user(self, clean_context_vars) -> None:
        """Test context manager with None as user (edge case)."""
        # Set initial user
        initial_user = MagicMock()
        initial_user.id = 999
        initial_token = current_user_ctx_var.set(initial_user)

        try:
            assert current_user_ctx_var.get() is initial_user

            # Use context manager with None
            with override_current_user(None):
                assert current_user_ctx_var.get() is None

            # Should restore to initial user
            assert current_user_ctx_var.get() is initial_user

        finally:
            current_user_ctx_var.reset(initial_token)

    def test_proper_token_management(
        self,
        clean_context_vars,
        mock_user: User,
        context_token_tracker,
    ) -> None:
        """Test that context manager uses proper token management."""
        # Track all tokens to verify proper cleanup
        tokens_used = []

        # Mock current_user_ctx_var.set to track tokens
        original_set = current_user_ctx_var.set

        def tracking_set(value):
            token = original_set(value)
            tokens_used.append(token)
            return token

        # Temporarily replace set method
        current_user_ctx_var.set = tracking_set

        try:
            with override_current_user(mock_user):
                # Should have created one token
                assert len(tokens_used) == 1
                assert current_user_ctx_var.get() is mock_user

                # Nested context
                with override_current_user(mock_user):
                    # Should have created another token
                    assert len(tokens_used) == 2
                    assert current_user_ctx_var.get() is mock_user

                # Back to single token state
                assert current_user_ctx_var.get() is mock_user

            # All contexts should be cleaned up
            assert current_user_ctx_var.get() is None

        finally:
            # Restore original set method
            current_user_ctx_var.set = original_set

    def test_thread_safety(
        self,
        clean_context_vars,
        mock_user: User,
    ) -> None:
        """Test context manager thread safety."""
        results = {}

        def thread1_work() -> None:
            user1 = MagicMock()
            user1.id = 111
            user1.email = "thread1@example.com"

            with override_current_user(user1):
                # Store what this thread sees
                results["thread1"] = current_user_ctx_var.get()

        def thread2_work() -> None:
            # Thread 2 should not see thread 1's user initially
            results["thread2_initial"] = current_user_ctx_var.get()

            user2 = MagicMock()
            user2.id = 222
            user2.email = "thread2@example.com"

            with override_current_user(user2):
                # Store what this thread sees
                results["thread2"] = current_user_ctx_var.get()

            # After context, should be None again
            results["thread2_after"] = current_user_ctx_var.get()

        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(thread1_work)
            future2 = executor.submit(thread2_work)

            future1.result()
            future2.result()

        # Verify thread isolation
        assert results["thread2_initial"] is None
        assert results["thread2_after"] is None
        assert results["thread1"].id == 111
        assert results["thread2"].id == 222

    @pytest.mark.asyncio
    async def test_async_context_safety(
        self,
        clean_context_vars,
        mock_user: User,
    ) -> None:
        """Test context manager in async environments."""
        results = {}

        async def task1() -> None:
            user1 = MagicMock()
            user1.id = 333
            user1.email = "task1@example.com"

            with override_current_user(user1):
                # Yield control
                await asyncio.sleep(0.01)
                results["task1"] = current_user_ctx_var.get()

        async def task2() -> None:
            # Task 2 should not see task 1's user initially
            results["task2_initial"] = current_user_ctx_var.get()

            user2 = MagicMock()
            user2.id = 444
            user2.email = "task2@example.com"

            with override_current_user(user2):
                # Yield control
                await asyncio.sleep(0.01)
                results["task2"] = current_user_ctx_var.get()

            # After context, should be None again
            results["task2_after"] = current_user_ctx_var.get()

        # Run tasks concurrently
        await asyncio.gather(task1(), task2())

        # Verify task isolation
        assert results["task2_initial"] is None
        assert results["task2_after"] is None
        assert results["task1"].id == 333
        assert results["task2"].id == 444

    def test_context_manager_return_value(
        self,
        clean_context_vars,
        mock_user: User,
    ) -> None:
        """Test that context manager returns the expected value."""
        # Context manager should yield None
        with override_current_user(mock_user) as result:
            assert result is None
            assert current_user_ctx_var.get() is mock_user

    def test_context_manager_with_complex_user_object(
        self,
        clean_context_vars,
    ) -> None:
        """Test context manager with complex user object."""
        # Create a more complex user-like object
        class MockComplexUser:
            def __init__(self, user_id: int, email: str) -> None:
                self.id = user_id
                self.email = email
                self.name = f"User {user_id}"
                self.roles = ["user"]
                self.is_active = True
                self.metadata = {"created": "2023-01-01", "last_login": "2023-12-31"}

            def __repr__(self) -> str:
                return f"User(id={self.id}, email='{self.email}')"

        complex_user = MockComplexUser(user_id=12345, email="complex@example.com")

        with override_current_user(complex_user):
            retrieved_user = current_user_ctx_var.get()

            assert retrieved_user is complex_user
            assert retrieved_user.id == 12345
            assert retrieved_user.email == "complex@example.com"
            assert retrieved_user.name == "User 12345"
            assert retrieved_user.roles == ["user"]
            assert retrieved_user.is_active is True
            assert retrieved_user.metadata["created"] == "2023-01-01"

    def test_multiple_sequential_context_uses(
        self,
        clean_context_vars,
    ) -> None:
        """Test using context manager multiple times in sequence."""
        users = []
        for i in range(5):
            user = MagicMock()
            user.id = 1000 + i
            user.email = f"sequential{i}@example.com"
            users.append(user)

        # Use context manager sequentially (not nested)
        for user in users:
            assert current_user_ctx_var.get() is None

            with override_current_user(user):
                assert current_user_ctx_var.get() is user
                assert current_user_ctx_var.get().id == user.id

            assert current_user_ctx_var.get() is None

    def test_context_manager_with_generator_function(
        self,
        clean_context_vars,
        mock_user: User,
    ) -> None:
        """Test context manager behavior when used within a generator function."""
        def user_context_generator():
            # Before context
            yield current_user_ctx_var.get()

            with override_current_user(mock_user):
                # Within context
                yield current_user_ctx_var.get()

            # After context
            yield current_user_ctx_var.get()

        gen = user_context_generator()

        before = next(gen)
        within = next(gen)
        after = next(gen)

        assert before is None
        assert within is mock_user
        assert after is None

    def test_context_manager_cleanup_on_system_exit(
        self,
        clean_context_vars,
        mock_user: User,
    ) -> None:
        """Test context manager cleanup on SystemExit exception."""
        # SystemExit should still trigger cleanup
        with pytest.raises(SystemExit), override_current_user(mock_user):
            assert current_user_ctx_var.get() is mock_user
            msg = "Test system exit"
            raise SystemExit(msg)

        # Context should still be cleaned up
        assert current_user_ctx_var.get() is None

    def test_context_manager_cleanup_on_keyboard_interrupt(
        self,
        clean_context_vars,
        mock_user: User,
    ) -> None:
        """Test context manager cleanup on KeyboardInterrupt."""
        # KeyboardInterrupt should still trigger cleanup
        with pytest.raises(KeyboardInterrupt), override_current_user(mock_user):
            assert current_user_ctx_var.get() is mock_user
            msg = "Test keyboard interrupt"
            raise KeyboardInterrupt(msg)

        # Context should still be cleaned up
        assert current_user_ctx_var.get() is None

    def test_context_manager_docstring_example(
        self,
        clean_context_vars,
    ) -> None:
        """Test the example given in the function's docstring."""
        # Simulate the docstring example
        user = MagicMock()
        user.id = 1
        user.email = "john_doe@example.com"

        with override_current_user(user):
            # Within this block, current user should be accessible
            current_user = current_user_ctx_var.get()
            assert current_user.email == user.email
            assert current_user.id == user.id

        # User context is automatically cleaned up
        assert current_user_ctx_var.get() is None

    def test_context_manager_preserves_original_user_on_exception(
        self,
        clean_context_vars,
    ) -> None:
        """Test that original user context is preserved when exception occurs."""
        original_user = MagicMock()
        original_user.id = 999
        original_user.email = "original@example.com"

        temporary_user = MagicMock()
        temporary_user.id = 111
        temporary_user.email = "temporary@example.com"

        # Set original user
        original_token = current_user_ctx_var.set(original_user)

        try:
            assert current_user_ctx_var.get() is original_user

            # Use context manager with exception
            with pytest.raises(ValueError), override_current_user(temporary_user):
                assert current_user_ctx_var.get() is temporary_user
                msg = "Test error"
                raise ValueError(msg)

            # Should restore to original user
            assert current_user_ctx_var.get() is original_user

        finally:
            current_user_ctx_var.reset(original_token)
