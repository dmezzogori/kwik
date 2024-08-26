from __future__ import annotations

from typing import Annotated

from fastapi import Depends


def _filters(filter: str | None = None, value: str | None = None) -> dict[str, str]:
    """
    Filter query parameter parser, to be used as endpoint dependency.
    """

    if filter is not None and value is not None:
        return {filter: value}

    return {}


FilterQuery = Annotated[dict[str, str], Depends(_filters)]
