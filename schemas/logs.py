from app.kwik import models
from app.kwik.schemas.synth import synth_schemas

LogBaseSchema, LogCreateSchema, LogUpdateSchema = synth_schemas(models.Log)
