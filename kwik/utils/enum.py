from __future__ import annotations

import enum


def merge_str_enum(name: str, *args):
    return enum.StrEnum(name, [(e, e) for arg in args for e in arg])
