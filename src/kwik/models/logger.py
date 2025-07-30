from sqlalchemy import JSON, Column, Integer, String

from kwik.database import base


class Log(base.Base):
    """Database model for storing application event logs."""

    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, nullable=True)
    entity = Column(String, nullable=True)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
