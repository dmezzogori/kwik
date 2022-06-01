from fastapi import HTTPException, status


class KwikException(Exception):
    """Base class for all Kwik exceptions."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code: int = status_code
        self.detail: str = detail
        super().__init__()

    @property
    def http_exc(self):
        return HTTPException(status_code=self.status_code, detail=self.detail)


class DuplicatedEntity(KwikException):
    def __init__(self, detail="Entity already exists"):
        super().__init__(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=detail)


class Forbidden(KwikException):
    def __init__(self, detail="Not enough privileges"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFound(KwikException):
    def __init__(self, detail="Entity not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
