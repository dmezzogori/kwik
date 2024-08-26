from .record_info import RecordInfoMixin


class SoftDeleteMixin(RecordInfoMixin):
    """
    Mixin for soft delete.
    """

    deleted: bool
