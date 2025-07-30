from pydantic import BaseModel


class RecoverPassword(BaseModel):
    """Schema for password recovery requests with user email."""

    email: str
