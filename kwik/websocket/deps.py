from broadcaster import Broadcast
from kwik import settings

broadcast = Broadcast(f"postgres://postgres:{settings.POSTGRES_PASSWORD}@db/app")
