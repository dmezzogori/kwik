"""CRUD operations for audit records."""

from kwik import models

from . import auto_crud


class CRUDAudit(auto_crud.AutoCRUD):
    """CRUD operations for audit log entries."""


audit = CRUDAudit(models.Audit)
