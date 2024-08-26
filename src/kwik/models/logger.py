import kwik.database.base as base
from sqlalchemy import Column, Integer, JSON, String


class Log(base.Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, nullable=True)
    entity = Column(String, nullable=True)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
