from typing import Generator, TypeVar, Callable, Iterable, Any

T = TypeVar("T")


def yield_limited(*, item: Any, count: int, limit: int) -> Iterable[Any]:
    """
    To be used to iter over a collection of items, but limit the number of items to be returned.
    Example:
        >>> list(yield_limited(limit=100, l=list(range(10))))
        >>> [0, 1, 2]
        >>> c = 0
        >>> for i in range(10):
        >>>     c = yield from yield_limited(item=i, count=c, limit=3)
    """

    if count < limit:
        yield item
        count += 1
    return count


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
