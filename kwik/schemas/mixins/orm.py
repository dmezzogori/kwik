from pydantic import BaseModel


class ORMMixin(BaseModel):
    id: int

    class Config:
        orm_mode = True
