from fastapi import status

from .base import KwikException


class IncorrectCredentials(KwikException):
    def __init__(self, detail="Incorrect credentials"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class UserNotFound(KwikException):
    def __init__(self, detail="User not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UserInactive(KwikException):
    def __init__(self, detail="Inactive user"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
