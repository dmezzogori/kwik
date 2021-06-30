from fastapi import HTTPException, status


class Forbidden(HTTPException):
    def __init__(self, detail=None):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFound(HTTPException):
    def __init__(self, id: int, entity: str = "Item"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} with id={id} does not exist in the system",
        )


class UserNotInvolved(HTTPException):
    def __init__(self, user_id: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"User #{user_id} is not involved",
        )


class UserInactive(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Inactive user",
        )


class MethodNotAllowed(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
