# Boletín Oficial PBA - Análisis con IA

Sitio web que muestra los gastos y normas del Boletín Oficial de la **Provincia de Buenos Aires**, con resúmenes generados por IA para facilitar la comprensión ciudadana.

## 🔍 Fuente de Datos

- **Boletín Oficial**: [boletinoficial.gba.gob.ar](https://boletinoficial.gba.gob.ar/)
- **Sistema de Normas**: [normas.gba.gob.ar](https://normas.gba.gob.ar/)

## 🚀 Características

- **Gastos del Estado**: Licitaciones, contrataciones, adjudicaciones
- **Normas**: Leyes, decretos, resoluciones, disposiciones
- **Resúmenes con IA**: Cada entrada incluye un resumen claro en español
- **Actualización diaria**: GitHub Actions mantiene el sitio actualizado

## 📁 Estructura

```
boletin_pba_ai/
├── scraper/
│   └── scrape_boletin.py   # Scraper principal
├── docs/                    # GitHub Pages (sitio web)
│   ├── index.html
│   └── data.json
├── .github/workflows/
│   └── daily_update.yml    # Automatización diaria
└── requirements.txt
```

## 🔧 Uso Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar scraper
python scraper/scrape_boletin.py

# Servir sitio localmente
cd docs && python -m http.server 8000
```

## 🤖 API de IA

Usa [AMD GPT-OSS 120B Chatbot](https://huggingface.co/spaces/amd/gpt-oss-120b-chatbot) para generar resúmenes en español.

## 📄 Licencia

MIT - Datos públicos del Boletín Oficial de la Provincia de Buenos Aires.
