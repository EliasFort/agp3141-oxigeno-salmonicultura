# agp3141-oxigeno-salmonicultura

Proyecto final del curso AGP3141 *Visualización y Análisis de Datos Medioambientales* (MAGEA, UC).

**Pregunta:** ¿qué condiciones del agua (temperatura, oxígeno disuelto, salinidad) anteceden a los episodios de mortalidad de salmones en Los Lagos?

## Datos

| Fuente | Contenido | Estado |
|---|---|---|
| IFOP, sistema de monitoreo de las Agrupaciones de Concesiones de Salmonicultura ([API pública](https://acs.ifop.cl/api/docs/public/)) | Las 5 boyas de Los Lagos: promedios horarios de 13 variables (archivos `datos/brutos/ifop_<boya>_horario.csv`) | Descargado |
| Sernapesca, vía Ley de Transparencia (solicitud AH010T0009768) | Mortalidad mensual por agrupación de concesiones, especie y causa | En espera (plazo: fines de octubre 2026) |

### Boyas

| Boya | Zona | Datos desde |
|---|---|---|
| ACS1 | Estuario de Reloncaví | dic 2023 |
| ACS16 | Golfo de Ancud, costa continental | dic 2024 |
| ACS17A | Sector Hornopirén | dic 2024 |
| ACS10A | Chiloé central | nov 2022 |
| ACS11 | Sur de Chiloé | dic 2024 |

El script `01-eda.py` analiza la ACS10A, que es la serie más larga.

## Estructura

```
agp3141-oxigeno-salmonicultura/
├── datos/
│   ├── brutos/          # tal como vienen de la fuente; no se editan
│   └── procesados/      # generados por los scripts
├── scripts/
│   └── 01-eda.py        # análisis exploratorio y datos ausentes
├── figuras/
└── README.md
```

## Cómo reproducir

```
pip install pandas numpy matplotlib
python scripts/01-eda.py
```

Si `datos/brutos/ifop_acs10a_horario.csv` no existe, el script lo descarga de la API del IFOP.
