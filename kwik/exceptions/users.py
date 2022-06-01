from fastapi import status

from .base import KwikException


class UserInactive(KwikException):
    def __init__(self, detail="User is not active"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
