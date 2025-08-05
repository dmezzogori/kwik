"""Gunicorn WSGI server application wrapper for Kwik framework."""

from typing import Any

import gunicorn.app.base


class KwikGunicornApplication(gunicorn.app.base.BaseApplication):
    """Gunicorn WSGI application wrapper for Kwik framework with custom configuration."""

    def __init__(self, app: Any, options: dict[str, Any] | None = None) -> None:  # noqa: ANN401
        """Initialize Gunicorn application with WSGI app and options."""
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self) -> None:
        """Load configuration settings from options dict into Gunicorn config."""
        config = {key: value for key, value in self.options.items() if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self) -> Any:  # noqa: ANN401
        """Return the WSGI application instance to be served."""
        return self.application
