"""Enhanced APIRouter with automatic CRUD generation."""

from inspect import getmembers, ismodule
from types import ModuleType

from fastapi import APIRouter as _APIRouter

from kwik.core.settings import get_settings

from .auditor import AuditorRouter


class APIRouter(_APIRouter):
    """Extended FastAPI router with bulk module inclusion capabilities."""

    def include_many(self, package: ModuleType) -> None:
        """Include all router modules from a package with auto-generated prefixes and tags."""
        for module_name, module in getmembers(package, ismodule):
            if module_name == "tests" and not get_settings().TEST_ENV:
                continue

            router = getmembers(
                module,
                lambda x: isinstance(x, (_APIRouter, AuditorRouter)),
            )[0][1]

            self.include_router(
                router,
                tags=[module_name.replace("_", "-")],
                prefix=f"/{module_name.replace('_', '-')}",
            )
