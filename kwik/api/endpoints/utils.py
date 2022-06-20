from typing import Any

from fastapi import APIRouter
from pydantic.networks import EmailStr

import kwik
from kwik import models, schemas
from kwik.utils import send_test_email

router = APIRouter()


@router.post("/test-email/", response_model=schemas.Msg, status_code=201)
def test_email(email_to: EmailStr, current_user: models.User = kwik.current_user) -> Any:
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


@router.post("/test-db-switcher/")
def test_db_switcher() -> Any:
    """
    Test DB Switcher.
    """

    user_db = kwik.crud.user.get(id=1)
    with kwik.database.db_context_switcher() as db:
        db = db
    kwik.logger.error(kwik.crud.user.db.get_bind())
    kwik.logger.error(db.get_bind())
    return {"user": user_db.name}
