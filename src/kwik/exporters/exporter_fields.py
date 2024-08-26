from typing import Any, Iterable


class ExporterFields:
    @classmethod
    def _class_attrs(cls) -> Iterable[tuple[str, Any]]:
        for k, v in cls.__dict__.items():
            if not k.startswith("__") and not k.endswith("__"):
                yield k, v

    @classmethod
    def as_dict(cls) -> dict[str, Any]:
        return {k: v for k, v in cls._class_attrs()}
