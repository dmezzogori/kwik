from kwik.models import Log
from .auto_crud import AutoCRUDCreate


class CRUDLogs(AutoCRUDCreate):
    pass


logs = CRUDLogs(Log)
