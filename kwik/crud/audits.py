from . import auto_crud

from kwik import models


class CRUDAudit(auto_crud.AutoCRUD):
    pass


audit = CRUDAudit(models.Audit)
