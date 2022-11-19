# First steps

To run your first Kwik application, once you have [installed](/#installation) it
all you need to do is to create a file named `app.py` with the following content:

```python
from kwik import Kwik, run
from kwik.api.api import api_router

app = Kwik(api_router)

run(app)
```

Then run it with:

<div class="termy">

```console
$ python app.py

KwikApp ready
KwikApp running on http://localhost:8080
Swagger available at http://localhost:8080/docs
```

</div>

The `run()` function will start a development server on port `8080`, with hot-reloading enabled.

Just point your browser to http://localhost:8080/docs, and you will see the automatic interactive API documentation.

![OpenAPI](/img/openapi.jpeg)

## What just happened?

The `Kwik` class is the main entry point for your application.

It takes a list of routers, which are the components that define the endpoints of your application.

In this case, we are using the `api_router` from `kwik.api.api`, which is the default router for the built-in endpoints.
The default endpoints, as they can be seen in the above picture, are:

 - `/api/v1/login`: to handle user authentication and token generation.
 - `/api/v1/users`: to handle user management.
 - `/api/v1/roles`: to handle role management.
 - `/api/v1/permissions`: to handle permission management.

## Next steps

Now that you have your first Kwik application running, you are probabily interested in the following:

 - how is the configuration handled? Go to the [configuration tutorial](configuration.md).
 - you can go to the [endpoints tutorial](endpoints.md) to learn how to add your own endpoints.
 - you can go to the [database tutorial](database.md) to learn how to use the database.