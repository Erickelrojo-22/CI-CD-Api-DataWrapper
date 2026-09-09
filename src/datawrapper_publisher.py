"""
Datawrapper Publisher — Actualiza y republica gráficos en Datawrapper vía API v3.

Uso:
    python src/datawrapper_publisher.py --csv-path data/cobertura_modulos.csv

Variables de entorno requeridas:
    DATAWRAPPER_API_TOKEN   Token de API con scopes chart:read y chart:write.
    DATAWRAPPER_CHART_ID    ID del gráfico existente a actualizar.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from urllib.parse import quote

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
BASE_URL = "https://api.datawrapper.de/v3/charts"
EMBED_BASE_URL = "https://datawrapper.dwcdn.net"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_dotenv() -> None:
    """Carga variables desde .env si existen y no están definidas en el entorno."""
    if not ENV_PATH.is_file():
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


# ---------------------------------------------------------------------------
# Cliente de la API de Datawrapper
# ---------------------------------------------------------------------------
class DatawrapperClient:
    """Cliente ligero para actualizar datos y republicar gráficos en Datawrapper."""

    def __init__(self, api_token: str, chart_id: str) -> None:
        if not api_token:
            raise ValueError("El token de API de Datawrapper no puede estar vacío.")
        if not chart_id:
            raise ValueError("El ID del gráfico de Datawrapper no puede estar vacío.")

        self.api_token = api_token
        self.chart_id = chart_id
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {self.api_token}"})

    # ----- Actualizar datos del gráfico -----
    def update_data(self, csv_path: str | Path) -> None:
        """Lee un archivo CSV y lo envía al endpoint PUT /charts/{id}/data.

        Args:
            csv_path: Ruta al archivo CSV con los datos a inyectar.

        Raises:
            FileNotFoundError: Si el archivo CSV no existe.
            requests.HTTPError: Si la API responde con un código de error.
        """
        csv_path = Path(csv_path)
        if not csv_path.is_file():
            raise FileNotFoundError(f"Archivo CSV no encontrado: {csv_path}")

        # Leer como bytes, eliminar BOM si existe y normalizar saltos de línea a LF.
        raw = csv_path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        csv_bytes = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

        url = f"{BASE_URL}/{self.chart_id}/data"

        logger.info("Actualizando datos del gráfico %s …", self.chart_id)
        response = self._session.put(
            url,
            data=csv_bytes,
            headers={"Content-Type": "text/csv"},
        )
        response.raise_for_status()
        logger.info(
            "Datos actualizados correctamente (HTTP %d).", response.status_code
        )

    # ----- Republicar el gráfico -----
    def publish(self) -> dict:
        """Republica el gráfico para que los cambios se reflejen en el embed.

        Returns:
            dict con la respuesta JSON de la API (incluye URL pública e iframe).

        Raises:
            requests.HTTPError: Si la API responde con un código de error.
        """
        url = f"{BASE_URL}/{self.chart_id}/publish"

        logger.info("Republicando gráfico %s …", self.chart_id)
        response = self._session.post(url)
        response.raise_for_status()

        result = response.json()
        public_url = result.get("data", {}).get("publicUrl", "N/A")
        logger.info("Gráfico publicado exitosamente.")
        logger.info("URL pública: %s", public_url)
        return result

    def fallback_public_url(self) -> str:
        """Construye la URL pública estándar del embed si la API no la devuelve."""
        safe_chart_id = quote(self.chart_id.strip(), safe="")
        return f"{EMBED_BASE_URL}/{safe_chart_id}/"

    # ----- Flujo completo -----
    def run(self, csv_path: str | Path) -> dict:
        """Ejecuta el flujo completo: actualizar datos → republicar gráfico.

        Args:
            csv_path: Ruta al archivo CSV.

        Returns:
            dict con la respuesta de publicación.
        """
        self.update_data(csv_path)
        return self.publish()


# ---------------------------------------------------------------------------
# Entrypoint CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Actualiza y republica un gráfico de Datawrapper con datos CSV.",
    )
    parser.add_argument(
        "--csv-path",
        default="data/cobertura_modulos.csv",
        help="Ruta al archivo CSV con los datos (default: data/cobertura_modulos.csv).",
    )
    parser.add_argument(
        "--skip-publish",
        action="store_true",
        help="Solo sube los datos. Útil para demostrar que publicar es un paso aparte.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    load_dotenv()

    api_token = os.environ.get("DATAWRAPPER_API_TOKEN", "")
    chart_id = os.environ.get("DATAWRAPPER_CHART_ID", "")

    if not api_token:
        logger.error(
            "Variable de entorno DATAWRAPPER_API_TOKEN no definida. Abortando."
        )
        sys.exit(1)

    if not chart_id:
        logger.error(
            "Variable de entorno DATAWRAPPER_CHART_ID no definida. Abortando."
        )
        sys.exit(1)

    client = DatawrapperClient(api_token=api_token, chart_id=chart_id)

    try:
        client.update_data(args.csv_path)
        result = {} if args.skip_publish else client.publish()
        public_url = (
            result.get("data", {}).get("publicUrl")
            if result
            else client.fallback_public_url()
        )
        public_url = public_url or client.fallback_public_url()
        iframe = (
            '<iframe title="Datawrapper chart" '
            f'src="{public_url}" scrolling="no" frameborder="0" '
            'style="width:0;min-width:100%!important;border:none;" '
            'height="520"></iframe>'
        )
        print(f"\n{'='*60}")
        status = "Datos actualizados" if args.skip_publish else "Grafico actualizado y publicado"
        print(f"  [OK] {status} exitosamente")
        print(f"  Chart ID : {chart_id}")
        print(f"  URL      : {public_url}")
        print(f"  Iframe   : {iframe}")
        print(f"{'='*60}\n")
    except FileNotFoundError as exc:
        logger.error(str(exc))
        sys.exit(1)
    except requests.HTTPError as exc:
        logger.error("Error de la API de Datawrapper: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
