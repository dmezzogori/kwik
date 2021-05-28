from sqlalchemy import Column, Integer, String, JSON

from app.kwik.db import Base


class Logging(Base):
    __tablename__ = 'logging'

    id = Column(Integer, primary_key=True, index=True)
    entity = Column(String)
    before = Column(JSON)
    after = Column(JSON)
