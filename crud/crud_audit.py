from auto_crud import AutoCRUD
from kwik.models import Audit


class CRUDAudit(AutoCRUD):
    pass


audit = CRUDAudit(Audit)
