# CI/CD — API Datawrapper

Automatización de la actualización y publicación de gráficos en [Datawrapper](https://www.datawrapper.de/) mediante su API v3, integrada en un pipeline CI/CD con GitHub Actions.

## 📋 Descripción

Este proyecto toma un archivo CSV con métricas de cobertura de pruebas unitarias, lo inyecta en un gráfico existente de Datawrapper vía API y republica la visualización para reflejar los cambios en el dashboard embebido.

### Flujo

```
CSV actualizado → PUT /charts/{id}/data → POST /charts/{id}/publish → Gráfico actualizado
```

## 🔧 Prerequisitos

- **Python 3.9+**
- **Token de API de Datawrapper** con scopes `chart:read` y `chart:write`
  - Genéralo en: Datawrapper → Settings → API Access Tokens
- **ID del gráfico** existente en Datawrapper

## 🚀 Setup Local

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

## ▶️ Uso

### Ejecución local

```bash
python src/datawrapper_publisher.py --csv-path data/cobertura_modulos.csv
```

### Ejecutar tests

```bash
python -m pytest tests/ -v
```

Los tests usan mocks de la API — no requieren token ni conexión real.

## 🔄 CI/CD (GitHub Actions)

El workflow se ejecuta automáticamente cuando:

- Se hace push a `main` con cambios en `data/` (el CSV).
- Se ejecuta manualmente (workflow_dispatch).

### Configuración de Secrets

En GitHub → Settings → Secrets and variables → Actions, agrega:

| Secret | Descripción |
|--------|-------------|
| `DATAWRAPPER_API_TOKEN` | Token de API de Datawrapper |
| `DATAWRAPPER_CHART_ID` | ID del gráfico a actualizar |

## 📁 Estructura del Proyecto

```
├── data/
│   └── cobertura_modulos.csv         # Dataset con métricas de cobertura
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

## 📊 Dataset de Ejemplo

| Módulo | Cobertura Actual (%) | Meta (%) |
|--------|---------------------|----------|
| Pasarela_Pagos | 94 | 90 |
| Autenticacion_OAuth | 88 | 85 |
| Motor_Recomendacion | 62 | 80 |
| Notificaciones_Push | 78 | 75 |
| Gestion_Inventario | 71 | 80 |
| Reportes_Financieros | 91 | 90 |

## 📚 Referencia API

- [Datawrapper API v3 Docs](https://developer.datawrapper.de/reference)
- **PUT** `/v3/charts/{id}/data` — Actualizar datos del gráfico
- **POST** `/v3/charts/{id}/publish` — Republicar el gráfico
