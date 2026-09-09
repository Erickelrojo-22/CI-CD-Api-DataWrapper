# CI/CD — API Datawrapper

Automatización de la actualización y publicación de gráficos en [Datawrapper](https://www.datawrapper.de/) mediante su API v3, integrada en un pipeline CI/CD con GitHub Actions.

## Que demuestra este proyecto

Este proyecto muestra cómo un programa externo puede actualizar un gráfico de Datawrapper sin entrar manualmente a la página web. El ejemplo toma un CSV con métricas de cobertura, lo sube a un gráfico existente usando la API y luego republica la visualización para que el dashboard embebido muestre los datos nuevos.

Flujo principal:

```
CSV actualizado → PUT /charts/{id}/data → POST /charts/{id}/publish → Gráfico actualizado
```

## Explicación rápida para presentar

Datawrapper es una herramienta web para crear visualizaciones de datos. En la web, una persona entra, carga o pega datos, elige el tipo de gráfico, ajusta colores, textos y diseño, y publica el resultado. Es ideal cuando quieres construir o editar una visualización de forma visual.

La API de Datawrapper es otra puerta de entrada al mismo servicio, pero pensada para programas. En lugar de hacer clics, un script manda peticiones HTTP a endpoints de Datawrapper. Con eso se puede crear gráficos, editar metadatos, subir datos, publicar visualizaciones, exportar imágenes o integrar el proceso dentro de un sistema propio.

La diferencia clave es esta:

| Web de Datawrapper | API de Datawrapper |
| --- | --- |
| La usa una persona con clics. | La usa un programa con peticiones HTTP. |
| Buena para diseñar y ajustar el gráfico. | Buena para automatizar tareas repetidas. |
| Actualizas datos manualmente. | Actualizas datos desde CSV, bases de datos o pipelines. |
| Publicas desde el editor web. | Publicas desde código con un token. |
| Sirve para exploración y diseño. | Sirve para integración, CI/CD y datos recurrentes. |

En este ejemplo usamos ambas partes: primero se crea y diseña el gráfico en la web de Datawrapper, y después el programa Python usa la API para reemplazar los datos y republicarlo.

## Cuando usar la API

Usa la API cuando los datos cambian seguido, cuando quieres actualizar muchos gráficos, cuando necesitas conectar Datawrapper con otra aplicación, cuando deseas que una tarea se ejecute automáticamente en GitHub Actions, o cuando no quieres que alguien repita el mismo proceso manual cada semana.

No hace falta usar la API si solo vas a crear un gráfico una vez, si todavía estás probando el diseño, o si los datos cambian muy poco y es más rápido actualizarlos desde la interfaz web.

## Como funciona tecnicamente

El script [src/datawrapper_publisher.py](/home/c0qux/Escritorio/CI-CD-Api-DataWrapper/src/datawrapper_publisher.py) hace esto:

1. Lee el token `DATAWRAPPER_API_TOKEN` y el ID del gráfico `DATAWRAPPER_CHART_ID`.
2. Lee el CSV [data/cobertura_modulos.csv](/home/c0qux/Escritorio/CI-CD-Api-DataWrapper/data/cobertura_modulos.csv).
3. Envía el CSV a `https://api.datawrapper.de/v3/charts/{id}/data` con método `PUT`.
4. Llama a `https://api.datawrapper.de/v3/charts/{id}/publish` con método `POST`.
5. Imprime la URL pública y un iframe que se puede incrustar en un dashboard.

El token debe quedarse en el servidor, terminal o GitHub Secrets. No se debe poner en HTML ni JavaScript del navegador.

## Demo para la clase

Abre el dashboard interactivo:

```bash
python3 src/dashboard_server.py
```

Luego entra a:

```text
http://localhost:8000/dashboard/
```

El dashboard ya queda conectado al gráfico `oduja`:

```text
https://datawrapper.dwcdn.net/oduja/3/
```

Para demostrar la actualización:

1. Cambia los valores en la tabla del dashboard.
2. Presiona `Publicar cambios`.
3. El servidor local guarda el CSV, llama la API y recarga el iframe con la versión publicada.

También puedes hacerlo desde terminal:

```bash
export DATAWRAPPER_API_TOKEN="tu_token_aqui"
export DATAWRAPPER_CHART_ID="tu_chart_id_aqui"
python3 src/datawrapper_publisher.py --csv-path data/cobertura_modulos.csv
```

## Guion corto

Puedes decir algo así:

> Nosotros investigamos Datawrapper, una herramienta para visualizar datos. Desde la web se diseña el gráfico de forma manual, pero la API permite que un programa lo actualice automáticamente. En nuestro ejemplo tenemos un CSV con métricas de cobertura. Cuando cambiamos el CSV, Python lo manda a Datawrapper con un `PUT`, luego publica el gráfico con un `POST`, y el dashboard embebido muestra la nueva versión. Esto serviría para reportes que se actualizan cada día, dashboards conectados a procesos automáticos o pipelines CI/CD.

## Prerequisitos

- **Python 3.9+**
- **Token de API de Datawrapper** con scopes `chart:read` y `chart:write`
  - Genéralo en: Datawrapper → Settings → API Access Tokens
- **ID del gráfico** existente en Datawrapper

## Setup Local

1. **Clonar el repositorio:**
   ```bash
   git clone <url-del-repo>
   cd CI-CD-Api-DataWrapper
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno:**
   ```bash
   cp .env.example .env
   # Editar .env con tu token y chart ID
   ```

   O exportarlas directamente:
   ```bash
   export DATAWRAPPER_API_TOKEN="tu_token_aqui"
   export DATAWRAPPER_CHART_ID="tu_chart_id_aqui"
   ```

## Uso

### Ejecución local

```bash
python3 src/datawrapper_publisher.py --csv-path data/cobertura_modulos.csv
```

Solo subir datos, sin republicar:

```bash
python3 src/datawrapper_publisher.py --csv-path data/cobertura_modulos.csv --skip-publish
```

### Ejecutar tests

```bash
python3 -m pytest tests/ -v
```

Los tests usan mocks de la API — no requieren token ni conexión real.

## CI/CD (GitHub Actions)

El workflow se ejecuta automáticamente cuando:

- Se hace push a `main` con cambios en `data/` (el CSV).
- Se ejecuta manualmente (workflow_dispatch).

### Configuración de Secrets

En GitHub → Settings → Secrets and variables → Actions, agrega:

| Secret | Descripción |
|--------|-------------|
| `DATAWRAPPER_API_TOKEN` | Token de API de Datawrapper |
| `DATAWRAPPER_CHART_ID` | ID del gráfico a actualizar |

## Estructura del Proyecto

```
├── data/
│   └── cobertura_modulos.csv         # Dataset con métricas de cobertura
├── dashboard/
│   └── index.html                    # Dashboard estático para presentar
├── src/
│   └── datawrapper_publisher.py      # Script principal (cliente API)
├── tests/
│   └── test_datawrapper_publisher.py # Tests unitarios
├── .github/
│   └── workflows/
│       └── publish-chart.yml         # Pipeline CI/CD
├── .env.example                      # Ejemplo de variables de entorno
├── requirements.txt                  # Dependencias Python
└── README.md                         # Este archivo
```

## Dataset de Ejemplo

| Módulo | Cobertura Actual (%) | Meta (%) |
|--------|---------------------|----------|
| Pasarela_Pagos | 94 | 90 |
| Autenticacion_OAuth | 88 | 85 |
| Motor_Recomendacion | 62 | 80 |
| Notificaciones_Push | 78 | 75 |
| Gestion_Inventario | 71 | 80 |
| Reportes_Financieros | 91 | 90 |

## Referencia API

- [Datawrapper API v3 Docs](https://developer.datawrapper.de/)
- **PUT** `/v3/charts/{id}/data` — Actualizar datos del gráfico
- **POST** `/v3/charts/{id}/publish` — Republicar el gráfico
