# Configuration

The configuration of a Kwik application is done through the use of environment variables.

The handling of the configuration is done by the <a href="https://pydantic-docs.helpmanual.io/" class="external-link" target="_blank">Pydantic</a> library, 
which is used by Kwik to validate the <a href="https://pydantic-docs.helpmanual.io/usage/settings/" class="external-link" target="_blank">settings</a>.

!!! Warning
    The configuration is done through environment variables, which are not secure. 
    You should not use them to store sensitive information, like passwords, tokens, etc.

    Instead, you should use the <a href="https://pydantic-docs.helpmanual.io/usage/settings/#secret-support" class="external-link" target="_blank">SecretStr</a> type, 
    which will read the values from environment variables, but will not show them in the documentation.

The following are the main configuration variables available, and corresponding default values:

 - **General**:
     - `SERVER_NAME`: `backend` - The name of the server/service on which the application is running (i.e. docker service name).
     - `HOST`: `localhost` - The hostname on which the application is running.
     - `PORT`: `8080` - The port on which the application is running.
     - `API_V1_STR`: `/api/v1` - The base path for the API.
     - `PROJECT_NAME`: `kwik` - The name of the project being developed.
 - **Database**:
     - `POSTGRES_SERVER`: `db` - The hostname of the database server.
     - `POSTGRES_DB`: `db` - The name of the database.
     - `POSTGRES_USER`: `postgres` - The username to use to connect to the database.
     - `POSTGRES_PASSWORD`: `root` - The password to use to connect to the database.
     - `ENABLE_SOFT_DELETE`: `False` - A flag to enable/disable soft delete.
 - **Mailserver**:
     - `SMTP_HOST`
     - `SMTP_PORT`
     - `SMTP_USER`
     - `SMTP_PASSWORD`
     - `SMTP_TLS`
 - **Superuser credentials**:
     - `FIRST_SUPERUSER`: `admin@example.com` - The email address of the admin superuser.
     - `FIRST_SUPERUSER_PASSWORD`: `admin` - The password of the admin superuser.
 - **Misc**:
     - `DEBUG`: `True` - A flag to enable/disable debug mode.
     - `HOTRELOAD`: `True` - A flag to enable/disable hot reloading.
     - `WEBSOCKET_ENABLED`: `False` - A flag to enable/disable websocket support.

!!! Note
    The default values are used only for development purposes. 
    In production, you should always override them with the appropriate values.

    Moreover, you should be aware that *environment variables names* are **case sensitive**.
