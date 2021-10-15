from typing import Any

from fastapi import APIRouter
from pydantic.networks import EmailStr

import kwik
from kwik import models, schemas
from kwik.core.celery_app import celery_app
from app.utils import send_test_email

router = APIRouter()


@router.post("/test-celery/", response_model=schemas.Msg, status_code=201)
def test_celery(msg: schemas.Msg, current_user: models.User = kwik.current_active_superuser,) -> Any:
    """
    Test Celery worker.
    """
    celery_app.send_task("app.worker.test_celery", args=[msg.msg])
    return {"msg": "Word received"}


@router.post("/test-email/", response_model=schemas.Msg, status_code=201)
def test_email(email_to: EmailStr, current_user: models.User = kwik.current_active_superuser,) -> Any:
    """
    Test emails.
    """
    send_test_email(email_to=email_to)
    return {"msg": "Test email sent"}


@router.post("/test-ws/")
async def test_ws(message: str, project_id: int) -> Any:
    """
    Test WS.
    """
    from kwik.websocket.deps import broadcast

    await broadcast.publish(channel=f"kanban_board_{project_id}", message=message)
    return {"message": f"{message}"}
