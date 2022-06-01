import enum
import os
from _csv import writer

from kwik.database.base import Base
from starlette.responses import StreamingResponse

from .base import KwikExporter


class CellFormats(enum.Enum):
    WRAP: str = "WRAP"
    DATE: str = ("DATE",)
    BOOL: str = "BOOL"
    INT: str = ("INT",)
    GENERIC: str = "GENERIC"
    SUBMODEL_WRAP: str = "SUBMODEL_WRAP"
    SUBMODEL_DATE: str = "SUBMODEL_DATE"
    SUBMODEL_BOOL: str = "SUBMODEL_BOOL"
    SUBMODEL_INT: str = "SUBMODEL_INT"
    SUBMODEL_GENERIC: str = "SUBMODEL_GENERIC"


class KwikCSVExporter(KwikExporter):
    file_extension = "csv"

    @staticmethod
    def _item_to_write(item: Base, field: str) -> bool:
        value = item.__getattribute__(field)
        return value is not None and value != ""

    def write_headers(self, writer_obj) -> None:
        headers = []
        for key in self.fields.as_dict().keys():
            if key in self.substitutions.keys():
                headers.append(self.substitutions[key])
            else:
                new_key = key
                for sub_key in self.partial_substitutions.keys():
                    if sub_key in new_key:
                        new_key = new_key.replace(sub_key, self.partial_substitutions[sub_key])
                else:
                    headers.append(new_key.replace("_", " ").capitalize())
        writer_obj.writerow(headers)

    def load(self, *, data: list[Base]) -> None:
        with open(self.filename, "w", newline="") as f:
            writer_obj = writer(f)
            self.write_headers(writer_obj)
            rows_to_write = []

            for item in data:
                items_to_write = []
                for field, field_type in self.fields.as_dict().items():
                    if getattr(item, field, None):
                        match field_type:
                            case CellFormats.DATE:
                                if self._item_to_write(item, field):
                                    items_to_write.append(item.__getattribute__(field).strftime("%Y-%m-%d"))
                                else:
                                    items_to_write.append("")
                            case CellFormats.INT:
                                if self._item_to_write(item, field):
                                    items_to_write.append(int(item.__getattribute__(field)))
                                else:
                                    items_to_write.append("")
                            case _:
                                items_to_write.append(item.__getattribute__(field))
                    else:
                        items_to_write.append("")
                rows_to_write.append(items_to_write)
            writer_obj.writerows(rows_to_write)

    def streaming_response(self) -> StreamingResponse:
        response = StreamingResponse(open(self.filename, mode="rb"), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename={self.filename}"
        os.remove(self.filename)
        return response
