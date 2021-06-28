from app.kwik import models, schemas
from .base import CRUDBase


class CRUDAudit(CRUDBase[models.Audit, schemas.AuditCreateSchema, schemas.AuditUpdateSchema]):
    pass


audit = CRUDAudit(models.Audit)
