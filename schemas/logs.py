from kwik import models
from kwik.schemas.synth import synth_schemas

LogBaseSchema, LogCreateSchema, LogUpdateSchema = synth_schemas(models.Log)
