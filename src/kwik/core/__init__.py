"""
Core framework package for kwik framework.

This package contains core framework components including configuration,
security utilities, and other foundational elements.
"""

from typing import Final

BCRYPT_MAX_PASSWORD_BYTES: Final[int] = 72
"""Maximum password length, in UTF-8 bytes, accepted by bcrypt.

bcrypt has always ignored input past 72 bytes. Up to and including bcrypt 4.x
the excess was truncated silently; bcrypt 5.0.0 raises ``ValueError`` instead.
This constant lives in ``core`` so both the hashing boundary (``kwik.security``)
and the request schemas (``kwik.schemas.user``) can enforce the same limit
without an import cycle -- ``kwik.security`` imports ``kwik.schemas``.
"""
