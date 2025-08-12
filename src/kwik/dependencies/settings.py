"""
Kwik dependency injection for application settings.

This module provides:
- Settings: Annotated dependency for injecting current settings into Kwik app routes
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from kwik.settings import BaseKwikSettings


def _get_settings(request: Request) -> BaseKwikSettings:
    return request.app.state.settings


Settings = Annotated[BaseKwikSettings, Depends(_get_settings)]

__all__ = ["Settings"]
