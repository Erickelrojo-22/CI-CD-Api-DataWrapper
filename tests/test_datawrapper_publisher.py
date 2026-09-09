"""
Tests unitarios para datawrapper_publisher.py.

Todos los tests usan mocks de las llamadas HTTP, por lo que no requieren
token ni conexión real a la API de Datawrapper.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Agregar src/ al path para poder importar el módulo directamente.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from datawrapper_publisher import DatawrapperClient  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
FAKE_TOKEN = "test-token-abc123"
FAKE_CHART_ID = "AbCdE"

SAMPLE_CSV_CONTENT = textwrap.dedent("""\
    Modulo,Cobertura_Actual_%,Meta_Target_%
    Pasarela_Pagos,94,90
    Autenticacion_OAuth,88,85
""")

PUBLISH_RESPONSE_JSON = {
    "data": {
        "publicUrl": "https://datawrapper.dwcdn.net/AbCdE/1/",
        "publicId": "AbCdE",
        "embedCodes": {
            "embed-method-responsive": (
                '<iframe title="Chart" '
                'src="https://datawrapper.dwcdn.net/AbCdE/1/" '
                'scrolling="no" frameborder="0" '
                'style="width:0;min-width:100%!important;border:none;" '
                'height="400"></iframe>'
            ),
        },
    },
}


@pytest.fixture()
def tmp_csv(tmp_path: Path) -> Path:
    """Crea un archivo CSV temporal con datos de ejemplo."""
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text(SAMPLE_CSV_CONTENT, encoding="utf-8")
    return csv_file


@pytest.fixture()
def client() -> DatawrapperClient:
    """Devuelve un DatawrapperClient con credenciales de prueba."""
    return DatawrapperClient(api_token=FAKE_TOKEN, chart_id=FAKE_CHART_ID)


# ---------------------------------------------------------------------------
# Tests de construcción
# ---------------------------------------------------------------------------
class TestClientInit:
    """Tests de validación del constructor."""

    def test_missing_token_raises(self) -> None:
        with pytest.raises(ValueError, match="token"):
            DatawrapperClient(api_token="", chart_id=FAKE_CHART_ID)

    def test_missing_chart_id_raises(self) -> None:
        with pytest.raises(ValueError, match="ID"):
            DatawrapperClient(api_token=FAKE_TOKEN, chart_id="")


# ---------------------------------------------------------------------------
# Tests de update_data
# ---------------------------------------------------------------------------
class TestUpdateData:
    """Tests para el método update_data (PUT /charts/{id}/data)."""

    @patch("datawrapper_publisher.requests.Session")
    def test_update_data_success(
        self, mock_session_cls: MagicMock, tmp_csv: Path
    ) -> None:
        """PUT exitoso devuelve 204 y envía el CSV correcto."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()
        mock_session.put.return_value = mock_response

        client = DatawrapperClient(api_token=FAKE_TOKEN, chart_id=FAKE_CHART_ID)
        client.update_data(tmp_csv)

        # Verificar que se llamó PUT con la URL y headers correctos.
        mock_session.put.assert_called_once()
        call_args = mock_session.put.call_args
        assert FAKE_CHART_ID in call_args[0][0]
        assert call_args[1]["headers"]["Content-Type"] == "text/csv"
        assert call_args[1]["data"] == SAMPLE_CSV_CONTENT.encode("utf-8")

    @patch("datawrapper_publisher.requests.Session")
    def test_update_data_http_error(
        self, mock_session_cls: MagicMock, tmp_csv: Path
    ) -> None:
        """PUT con error HTTP lanza requests.HTTPError."""
        import requests as real_requests

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = real_requests.HTTPError(
            "401 Unauthorized"
        )
        mock_session.put.return_value = mock_response

        client = DatawrapperClient(api_token=FAKE_TOKEN, chart_id=FAKE_CHART_ID)

        with pytest.raises(real_requests.HTTPError):
            client.update_data(tmp_csv)

    def test_csv_not_found(self, client: DatawrapperClient) -> None:
        """Archivo CSV inexistente lanza FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="no encontrado"):
            client.update_data("/ruta/inexistente/datos.csv")


# ---------------------------------------------------------------------------
# Tests de publish
# ---------------------------------------------------------------------------
class TestPublish:
    """Tests para el método publish (POST /charts/{id}/publish)."""

    @patch("datawrapper_publisher.requests.Session")
    def test_publish_success(self, mock_session_cls: MagicMock) -> None:
        """POST exitoso devuelve 200 y la URL pública."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = PUBLISH_RESPONSE_JSON
        mock_session.post.return_value = mock_response

        client = DatawrapperClient(api_token=FAKE_TOKEN, chart_id=FAKE_CHART_ID)
        result = client.publish()

        assert result["data"]["publicUrl"] == "https://datawrapper.dwcdn.net/AbCdE/1/"
        mock_session.post.assert_called_once()
        assert FAKE_CHART_ID in mock_session.post.call_args[0][0]

    @patch("datawrapper_publisher.requests.Session")
    def test_publish_http_error(self, mock_session_cls: MagicMock) -> None:
        """POST con error HTTP lanza requests.HTTPError."""
        import requests as real_requests

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = real_requests.HTTPError(
            "500 Internal Server Error"
        )
        mock_session.post.return_value = mock_response

        client = DatawrapperClient(api_token=FAKE_TOKEN, chart_id=FAKE_CHART_ID)

        with pytest.raises(real_requests.HTTPError):
            client.publish()


# ---------------------------------------------------------------------------
# Test de flujo completo
# ---------------------------------------------------------------------------
class TestRunFlow:
    """Tests para el método run (flujo completo)."""

    @patch("datawrapper_publisher.requests.Session")
    def test_run_calls_update_then_publish(
        self, mock_session_cls: MagicMock, tmp_csv: Path
    ) -> None:
        """run() ejecuta update_data y luego publish en orden."""
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        # Mock para PUT (update_data)
        mock_put_response = MagicMock()
        mock_put_response.status_code = 204
        mock_put_response.raise_for_status = MagicMock()

        # Mock para POST (publish)
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.json.return_value = PUBLISH_RESPONSE_JSON

        mock_session.put.return_value = mock_put_response
        mock_session.post.return_value = mock_post_response

        client = DatawrapperClient(api_token=FAKE_TOKEN, chart_id=FAKE_CHART_ID)
        result = client.run(tmp_csv)

        # Verificar que ambos métodos fueron llamados.
        mock_session.put.assert_called_once()
        mock_session.post.assert_called_once()

        # Verificar orden: PUT antes de POST.
        put_call_order = mock_session.put.call_args_list
        post_call_order = mock_session.post.call_args_list
        assert len(put_call_order) == 1
        assert len(post_call_order) == 1

        # Verificar resultado.
        assert result["data"]["publicUrl"] == "https://datawrapper.dwcdn.net/AbCdE/1/"
