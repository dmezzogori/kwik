from sqlalchemy import Column, Integer, String, JSON

from app.kwik.db import Base, RecordInfoMixin


class Log(Base):
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True, index=True)
    entity = Column(String)
    before = Column(JSON)
    after = Column(JSON)
