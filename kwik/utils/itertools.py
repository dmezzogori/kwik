from typing import Generator, TypeVar, Callable, Iterable

T = TypeVar("T")


def iter_unique(generator: Generator[T, None, None], *, attr: str | Callable) -> Iterable[T]:
    """restiuisce elementi unici dal generatore, in funzione del valore dell'attributo indicato"""
    seen = set()
    for t in generator:
        if isinstance(attr, str):
            x = getattr(t, attr)
        else:
            x = attr(t)
        if x in seen:
            continue
        seen.add(x)
        yield t
