"""Run the main entry point for the kwik command-line interface."""

import sys

import kwik


def main() -> None:
    """Run the main entry point for the kwik command-line interface."""
    if len(sys.argv) == 1:
        from kwik.api.api import api_router  # noqa: PLC0415

        k = kwik.Kwik(api_router)
        kwik.run(k)
    else:
        kwik.run(sys.argv[1])


if __name__ == "__main__":
    main()
