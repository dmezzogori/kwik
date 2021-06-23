from fastapi import HTTPException, status


class NotFound(HTTPException):
    def __init__(self, id: int, entity: str = 'The item'):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity} with id={id} does not exist in the system"
        )


class UserNotInvolved(HTTPException):
    def __init__(self, user_id: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The user #{user_id} is not involved"
        )
