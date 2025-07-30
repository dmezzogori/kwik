import gunicorn.app.base


class KwikGunicornApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        """Initialize Gunicorn application with WSGI app and options."""
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        """Load configuration settings from options dict into Gunicorn config."""
        config = {key: value for key, value in self.options.items() if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        """Return the WSGI application instance to be served."""
        return self.application
