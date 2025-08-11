from http import HTTPStatus

from fastapi.testclient import TestClient

from kwik.core.settings import BaseKwikSettings


class TestContextRouter:
    def test_get_settings(self, client: TestClient, settings: BaseKwikSettings) -> None:
        response = client.get("/api/v1/context/settings")

        status_code = response.status_code
        json_response = response.json()

        assert status_code == HTTPStatus.OK
        assert json_response["POSTGRES_SERVER"] == settings.POSTGRES_SERVER
        assert json_response["POSTGRES_PORT"] == settings.POSTGRES_PORT
        assert json_response["POSTGRES_DB"] == settings.POSTGRES_DB
        assert json_response["POSTGRES_USER"] == settings.POSTGRES_USER
        assert json_response["POSTGRES_PASSWORD"] == settings.POSTGRES_PASSWORD

    def test_get_session(self, client: TestClient) -> None:
        response = client.get("/api/v1/context/session")

        status_code = response.status_code
        json_response = response.json()

        assert status_code == HTTPStatus.OK
        assert json_response["ok"] is True
        assert json_response["db_rows"] == 1

        response = client.get("/api/v1/context/session")

        status_code = response.status_code
        json_response = response.json()

        assert status_code == HTTPStatus.OK
        assert json_response["ok"] is True
        assert json_response["db_rows"] == 2
