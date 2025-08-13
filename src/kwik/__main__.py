"""
Kwik CLI entry point module.

This module provides the command-line interface for the Kwik web framework.
It supports two modes of operation:

1. Default mode (no arguments):
   - Creates a Kwik application with default settings (BaseKwikSettings)
   - Uses the standard API router from kwik.api.api
   - Ideal for quick development and testing

2. Custom module mode (with arguments):
   - Accepts a module path as the first command-line argument
   - The specified module must contain an 'app' attribute with a FastAPI application
   - Useful for running custom applications built with Kwik

Usage Examples:
    # Run with default settings (development server on localhost:8080)
    $ kwik

    # Run a custom module
    $ kwik myproject.main

    # The custom module should have structure like:
    # myproject/main.py:
    #   app = FastAPI()  # or Kwik application instance
"""

import sys

from kwik import Kwik, run
from kwik.api.api import api_router
from kwik.settings import BaseKwikSettings


def main() -> None:
    """
    Entry point for the Kwik CLI application.

    This function handles command-line arguments and determines how to run the application:

    - No arguments: Creates and runs a default Kwik application with BaseKwikSettings
      and the standard API router. This is the typical development workflow.

    - With arguments: Passes the first argument as a module path to the run() function.
      The module path should point to a Python module containing an 'app' attribute
      with a FastAPI application instance.

    The run() function will automatically choose the appropriate server (uvicorn for
    development, gunicorn for production) based on the APP_ENV setting.

    Raises:
        SystemExit: If there are issues with the provided module path or application setup.

    """
    if len(sys.argv) == 1:
        # Default mode: no command-line arguments provided
        # Create default settings with development configuration
        settings = BaseKwikSettings()

        # Initialize Kwik application with default settings and standard API router
        kwik_app = Kwik(settings=settings, api_router=api_router)
        # Run the application (uvicorn will be used in development mode)
        run(kwik_app)
    else:
        # Custom module mode: first argument is treated as a module path
        # The run() function will import the module and look for an 'app' attribute
        run(sys.argv[1])


if __name__ == "__main__":
    main()
