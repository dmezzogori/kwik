"""Guard: a custom user model mapped without constructing a Kernel must fail loudly."""

from __future__ import annotations

import subprocess
import sys

# Runs in a fresh interpreter: a custom model maps the "users" table but no Kernel is
# constructed, so get_kernel() must refuse to materialize the DefaultUser fallback (which
# would collide on "users") and instead raise an actionable RuntimeError.
_PROBE = """
import kwik
from kwik.models import Base, UserMixin


class OtherUser(Base, UserMixin):
    __tablename__ = "users"


from kwik.kernel import get_kernel

try:
    get_kernel()
except RuntimeError as exc:
    assert "no Kernel was constructed" in str(exc), str(exc)
else:
    message = "expected RuntimeError when a custom user model is mapped without a Kernel"
    raise AssertionError(message)
"""


def test_forgotten_kernel_raises_actionable_error() -> None:
    """A mapped-but-unregistered custom user model makes get_kernel() raise, not silently default."""
    subprocess.run([sys.executable, "-c", _PROBE], check=True)  # noqa: S603
