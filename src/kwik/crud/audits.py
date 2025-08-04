"""CRUD operations for audit records."""

from kwik import models, schemas

from . import auto_crud


class CRUDAudit(auto_crud.AutoCRUD[models.Audit, schemas.AuditEntry, schemas.AuditProfile]):
    """CRUD operations for audit log entries."""


audit = CRUDAudit()
