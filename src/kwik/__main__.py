"""Run the main entry point for the kwik command-line interface."""

import sys

from kwik import Kwik, run
from kwik.api.api import api_router
from kwik.core.settings import BaseKwikSettings


def main() -> None:
    """Run the main entry point for the kwik command-line interface."""
    if len(sys.argv) == 1:
        settings = BaseKwikSettings()

        kwik_app = Kwik(settings, api_router)
        run(kwik_app)
    else:
        run(sys.argv[1])


if __name__ == "__main__":
    main()
