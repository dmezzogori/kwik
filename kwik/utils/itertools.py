from typing import Generator, TypeVar


T = TypeVar("T")


def iter_unique(generator: Generator[T, None, None], *, attr: str) -> T:
    """restiuisce elementi unici dal generatore, in funzione del valore dell'attributo indicato"""
    seen = set()
    for t in generator:
        x = getattr(t, attr)
        if x in seen:
            continue
        seen.add(x)
        yield t
