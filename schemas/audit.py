from kwik import models
from kwik.schemas.synth import synth_schemas

AuditBaseSchema, AuditCreateSchema, AuditUpdateSchema = synth_schemas(models.Audit)
