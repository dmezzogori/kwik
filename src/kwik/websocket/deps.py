"""WebSocket dependencies and broadcast configuration."""

from broadcaster import Broadcast

from kwik.core.settings import get_settings

broadcast = Broadcast(f"postgres://postgres:{get_settings().POSTGRES_PASSWORD}@db/app")
