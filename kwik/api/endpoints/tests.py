from typing import Any

from fastapi import APIRouter
from pydantic.networks import EmailStr

import kwik
from kwik import models, schemas
from kwik.utils import send_test_email

router = APIRouter()


@router.get("/get/")
def test_get(msg: str) -> Any:
    """
    Test a simple get.
    It returns the message you send.
    """
    return {"msg": msg}


@router.post("/post/")
def test_post(msg: str) -> Any:
    """
    Test a simple post.
    It returns the message you send.
    """
    return {"msg": msg}


@router.put("/put/")
def test_put(msg: str) -> Any:
    """
    Test a simple put.
    It returns the message you send.
    """
    return {"msg": msg}


@router.delete("/delete/")
def test_delete(msg: str) -> Any:
    """
    Test a simple delete.
    It returns the message you send.
    """
    return {"msg": msg}