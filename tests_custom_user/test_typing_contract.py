"""
Static typing contract for the kernel — checked by pyright in CI.

The probe functions are never executed; pyright verifies the assert_type claims.
ContractUser is deliberately NOT mapped (no Base subclass): pytest imports this
module in the custom-user session, and a second mapped "users" class would clash.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, assert_type

from kwik.crud.context import Context
from kwik.crud.users import CRUDUsers
from kwik.kernel import Kernel
from kwik.models import UserMixin

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.crud.context import MaybeUserCtx


class ContractUser(UserMixin):
    """Typing-only stand-in for a custom user model."""

    nickname: str


def _probe_kernel_typing(kernel: Kernel[ContractUser], context: MaybeUserCtx, some_user: UserMixin) -> None:
    assert_type(kernel.user_model, type[ContractUser])
    assert_type(kernel.crud_users, CRUDUsers[ContractUser])
    maybe_user = kernel.crud_users.get(entity_id=1, context=context)
    assert_type(maybe_user, ContractUser | None)
    assert_type(kernel.get_current_user(user=some_user), ContractUser)
    assert_type(kernel.get_resolved_user(user=some_user), ContractUser)


def _probe_context_typing(kernel: Kernel[ContractUser], db_session: Session, some_user: UserMixin) -> None:
    ctx = kernel.get_user_context(session=db_session, user=some_user)
    assert_type(ctx, Context[ContractUser])
    assert_type(ctx.user, ContractUser)


def _probe_constructor_inference() -> None:
    # Never executed: ContractUser is not a Base subclass, so constructing a real Kernel would
    # fail at runtime. pyright only needs to see that the constructor infers Kernel[ContractUser].
    assert_type(Kernel(user_model=ContractUser), Kernel[ContractUser])


def test_contract_module_imports() -> None:
    """The probes above are static-only; this keeps pytest collection meaningful."""
    assert callable(_probe_kernel_typing)
    assert callable(_probe_context_typing)
    assert callable(_probe_constructor_inference)
