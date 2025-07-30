from fastapi import HTTPException, status


class ExporterLimitExceeded(HTTPException):
    """Exception raised when export request exceeds allowed limits."""

    def __init__(self):
        """Initialize exporter limit exceeded exception."""
        super().__init__(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
