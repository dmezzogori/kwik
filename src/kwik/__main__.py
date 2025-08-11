"""Run the main entry point for the kwik command-line interface."""

if __name__ == "__main__":
    import sys

    from kwik import Kwik, run
    from kwik.api.api import api_router

    if len(sys.argv) == 1:
        k = Kwik(api_router)
        run(k)
    else:
        run(sys.argv[1])
