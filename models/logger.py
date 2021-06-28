from sqlalchemy import Column, Integer, JSON, String

from app.kwik.db import Base


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String)
    entity = Column(String)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
