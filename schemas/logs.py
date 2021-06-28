from app.kwik.schemas.synth import synth_schemas

from app.kwik.models import Log


LogBaseSchema, LogCreateSchema, LogUpdateSchema = synth_schemas(Log)
