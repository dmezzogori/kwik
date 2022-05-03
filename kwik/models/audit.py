from kwik.database.base import Base
from sqlalchemy import Column, Float, Integer, String


class Audit(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    client_host = Column(String, index=True, nullable=False)
    request_id = Column(String, nullable=True)
    user_id = Column(Integer, index=True, nullable=True)
    impersonator_user_id = Column(Integer, index=True, nullable=True)
    method = Column(String, index=True, nullable=False)
    headers = Column(String, nullable=False)
    url = Column(String, nullable=False)
    query_params = Column(String, nullable=True)
    path_params = Column(String, nullable=True)
    body = Column(String, nullable=True)
    process_time = Column(Float, nullable=True)
    status_code = Column(Integer, nullable=True)
