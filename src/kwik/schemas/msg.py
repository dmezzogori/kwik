"""Generic message schema for API responses."""

from pydantic import BaseModel


class Msg(BaseModel):
    """Generic message schema for API responses."""

    msg: str
