from inspect import getmembers, ismodule

from fastapi import APIRouter as _APIRouter

from .auditor import AuditorRouter
from .autorouter import AutoRouter


class APIRouter(_APIRouter):
    def include_many(self, package):
        for module_name, module in getmembers(package, ismodule):
            router = getmembers(module, lambda x: isinstance(x, (_APIRouter, AuditorRouter, AutoRouter)))[0][1]

            if isinstance(router, AutoRouter):
                router = router.router

            self.include_router(
                router,
                tags=[module_name.replace("_", "-")],
                prefix=f"/{module_name.replace('_', '-')}",
            )
