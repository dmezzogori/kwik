"""Run the main entry point for the kwik command-line interface."""

import sys

from kwik import Kwik, run
from kwik.api.api import api_router


def main() -> None:
    """Run the main entry point for the kwik command-line interface."""
    if len(sys.argv) == 1:
        k = Kwik(api_router)
        run(k)
    else:
        run(sys.argv[1])


if __name__ == "__main__":
    main()
