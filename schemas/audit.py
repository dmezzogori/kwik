from app.kwik.schemas.synth import synth_schemas

from app.kwik.models import Audit


AuditBaseSchema, AuditCreateSchema, AuditUpdateSchema = synth_schemas(Audit)
