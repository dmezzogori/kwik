from app import models
from app.kwik.schemas.synth import synth_schemas

AuditBaseSchema, AuditCreateSchema, AuditUpdateSchema = synth_schemas(models.Audit)
