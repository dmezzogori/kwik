import logging

from kwik import settings

# https://docs.python.org/3/library/logging.html
logging.basicConfig(level=settings.LOG_LEVEL)

# uvicorn_logger = logging.getLogger("uvicorn.error")
# uvicorn_logger.propagate = False

logger = logging.getLogger("kwik")
logger.setLevel(settings.LOG_LEVEL)
