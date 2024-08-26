from kwik.database.base import Base
from starlette.responses import StreamingResponse

from .exporter_fields import ExporterFields


class KwikExporter:
    file_extension: str
    substitutions: dict[str, str]
    partial_substitutions: dict[str, str]

    def __init__(self, fields: ExporterFields, filename: str | None = None) -> None:
        self.fields = fields
        self.already_written = False

        if filename is None:
            self.filename = f"export.{self.file_extension}"
        elif not filename.lower().endswith(self.file_extension):
            self.filename = f"{filename}.{self.file_extension}"
        else:
            self.filename = filename

    def load(self, data: list[Base]) -> None:
        raise NotImplementedError

    def streaming_response(self) -> StreamingResponse:
        raise NotImplementedError
