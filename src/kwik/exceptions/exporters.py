from fastapi import HTTPException, status


class ExporterLimitExceeded(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
