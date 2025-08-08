"""CRUD operations for audit records."""

from kwik.models import Audit
from kwik.schemas import AuditEntry, AuditProfile

from .autocrud import AutoCRUD


class CRUDAudit(AutoCRUD[Audit, AuditEntry, AuditProfile]):
    """CRUD operations for audit log entries."""


crud_audit = CRUDAudit()


__all__ = ["crud_audit"]
