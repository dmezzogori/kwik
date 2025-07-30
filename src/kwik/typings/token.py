"""Type definitions for authentication tokens."""

from __future__ import annotations

from typing import TypedDict


class Token(TypedDict):
    """Type definition for authentication token structure."""

    access_token: str
    token_type: str
