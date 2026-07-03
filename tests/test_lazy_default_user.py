"""Guard: importing kwik must not map DefaultUser (custom apps map their own users table)."""

from __future__ import annotations

import subprocess
import sys

_PROBE = (
    "import kwik; from kwik.models import Base; "
    "assert 'users' not in Base.metadata.tables, 'DefaultUser must not be eagerly mapped'"
)


def test_default_user_not_mapped_on_bare_import() -> None:
    """Run the probe in a fresh interpreter: the main test process has DefaultUser mapped already."""
    subprocess.run([sys.executable, "-c", _PROBE], check=True)  # noqa: S603
