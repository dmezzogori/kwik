from pydantic import BaseModel


class RecoverPassword(BaseModel):
    email: str
