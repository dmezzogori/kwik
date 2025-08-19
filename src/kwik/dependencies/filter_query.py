"""Filter query dependency for FastAPI endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends


def _filters(filter_key: str | None = None, value: str | None = None) -> dict[str, str]:
    """Filter query parameter parser, to be used as endpoint dependency."""
    if filter_key is not None and value is not None:
        return {filter_key: value}

    return {}


Filters = Annotated[dict[str, str], Depends(_filters)]


__all__ = ["Filters"]
