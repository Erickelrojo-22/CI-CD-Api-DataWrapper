"""
Servidor local para presentar la demo de Datawrapper.

Sirve el dashboard, permite editar el CSV desde la página y publica los cambios
en el gráfico configurado con DATAWRAPPER_CHART_ID.
"""

from __future__ import annotations

import csv
import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import requests

from datawrapper_publisher import DatawrapperClient

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "cobertura_modulos.csv"
ENV_PATH = ROOT / ".env"
DEFAULT_CHART_ID = "oduja"
DEFAULT_PUBLIC_URL = "https://datawrapper.dwcdn.net/oduja/4/"


def load_dotenv() -> None:
    if not ENV_PATH.is_file():
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def read_rows() -> list[dict[str, str]]:
    with DATA_PATH.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def write_rows(rows: list[dict[str, Any]]) -> None:
    fieldnames = ["Modulo", "Cobertura_Actual_%", "Meta_Target_%"]
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "Modulo": str(row.get("Modulo", "")).strip(),
                    "Cobertura_Actual_%": int(row.get("Cobertura_Actual_%", 0)),
                    "Meta_Target_%": int(row.get("Meta_Target_%", 0)),
                }
            )


def chart_url(chart_id: str) -> str:
    safe_chart_id = quote(chart_id.strip(), safe="")
    return f"https://datawrapper.dwcdn.net/{safe_chart_id}/"


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            self.send_json(
                {
                    "chartId": os.environ.get("DATAWRAPPER_CHART_ID", DEFAULT_CHART_ID),
                    "publicUrl": DEFAULT_PUBLIC_URL,
                }
            )
            return

        if parsed.path == "/api/data":
            self.send_json({"rows": read_rows()})
            return

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/publish":
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint no encontrado")
            return

        try:
            payload = self.read_json()
            rows = payload.get("rows", [])
            if not isinstance(rows, list) or not rows:
                raise ValueError("No se recibieron filas para publicar.")

            write_rows(rows)

            api_token = os.environ.get("DATAWRAPPER_API_TOKEN", "")
            chart_id = os.environ.get("DATAWRAPPER_CHART_ID", DEFAULT_CHART_ID)
            client = DatawrapperClient(api_token=api_token, chart_id=chart_id)
            result = client.run(DATA_PATH)
            public_url = (
                result.get("data", {}).get("publicUrl")
                or DEFAULT_PUBLIC_URL
                or chart_url(chart_id)
            )
            self.send_json(
                {
                    "ok": True,
                    "chartId": chart_id,
                    "publicUrl": public_url,
                    "rows": read_rows(),
                }
            )
        except (ValueError, FileNotFoundError) as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except requests.HTTPError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            self.send_json(
                {"ok": False, "error": f"Error de Datawrapper: {detail}"},
                HTTPStatus.BAD_GATEWAY,
            )

    def read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        return json.loads(raw_body.decode("utf-8"))

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    load_dotenv()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"Dashboard listo en http://localhost:{port}/dashboard/")
    server.serve_forever()


if __name__ == "__main__":
    main()
