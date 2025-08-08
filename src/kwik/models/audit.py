"""Database model for audit log entries."""

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from kwik.models.base import Base


class Audit(Base):
    """Database model for storing HTTP request audit logs."""

    __tablename__ = "audits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_host: Mapped[str] = mapped_column(String, index=True)
    request_id: Mapped[str | None] = mapped_column(String)
    user_id: Mapped[int | None] = mapped_column(index=True)
    impersonator_user_id: Mapped[int | None] = mapped_column(index=True)
    method: Mapped[str] = mapped_column(String, index=True)
    headers: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    query_params: Mapped[str | None] = mapped_column(String)
    path_params: Mapped[str | None] = mapped_column(String)
    body: Mapped[str | None] = mapped_column(String)
    process_time: Mapped[float | None] = mapped_column(Float)
    status_code: Mapped[int | None] = mapped_column()
