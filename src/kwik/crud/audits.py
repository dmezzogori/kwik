from kwik import models

from . import auto_crud


class CRUDAudit(auto_crud.AutoCRUD):
    pass


audit = CRUDAudit(models.Audit)
