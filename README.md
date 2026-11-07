# agp3141-oxigeno-salmonicultura

Proyecto final del curso AGP3141 *Visualización y Análisis de Datos Medioambientales* (MAGEA, UC).

**Pregunta:** ¿qué condiciones del agua (temperatura, oxígeno disuelto, salinidad) anteceden a los episodios de mortalidad de salmones en Los Lagos?

## Datos

| Fuente | Contenido | Estado |
|---|---|---|
| IFOP, sistema de monitoreo de las Agrupaciones de Concesiones de Salmonicultura ([API pública](https://acs.ifop.cl/api/docs/public/)) | Las 5 boyas de Los Lagos: promedios horarios de 13 variables (archivos `datos/brutos/ifop_<boya>_horario.csv`) | Descargado |
| Sernapesca, vía Ley de Transparencia (solicitud AH010T0009768, ORD. DN-05691/2026) | Mortalidad semanal de salmónidos por región, comuna, especie y causa (ene 2017 a sept 2026) y existencias mensuales por comuna (ene 2017 a ago 2026), en `datos/brutos/sernapesca/` | Recibido. El Excel de mortalidad (~200 MB) no se sube a GitHub; su versión agregada está en `datos/procesados/` |

### Boyas

| Boya | Zona | Datos desde |
|---|---|---|
| ACS1 | Estuario de Reloncaví | dic 2023 |
| ACS16 | Golfo de Ancud, costa continental | dic 2024 |
| ACS17A | Sector Hornopirén | dic 2024 |
| ACS10A | Chiloé central | nov 2022 |
| ACS11 | Sur de Chiloé | dic 2024 |

El script `01-eda.py` analiza la ACS10A, que es la serie más larga.

Sernapesca entregó la mortalidad por comuna (no por agrupación de concesiones), así que cada boya se asigna a la comuna donde está: ACS1 → Cochamó, ACS10A → Puqueldón, ACS11 → Queilén, ACS16 → Chaitén, ACS17A → Hualaihué.

## Estructura

```
agp3141-oxigeno-salmonicultura/
├── datos/
│   ├── brutos/          # tal como vienen de la fuente; no se editan
│   └── procesados/      # generados por los scripts
├── scripts/
│   ├── 01-eda.py                        # análisis exploratorio y datos ausentes
│   ├── 05-sernapesca.py                 # lee los Excel de Sernapesca -> CSV
│   └── 06-cruce-boyas-mortalidad.py     # oxígeno vs. tasa de mortalidad por comuna
├── figuras/
└── README.md
```

## Cómo reproducir

```
pip install pandas numpy matplotlib scipy openpyxl
python scripts/01-eda.py
python scripts/05-sernapesca.py
python scripts/06-cruce-boyas-mortalidad.py
```

Si `datos/brutos/ifop_acs10a_horario.csv` no existe, el script lo descarga de la API del IFOP.

## Hallazgo 3: oxígeno profundo y mortalidad

Tasa de mortalidad mensual = peces muertos por causa *Ambiental* / existencias del mes × 100, cruzada con el promedio mensual de cada boya (`figuras/05-…` y `figuras/06-…`).

- En las boyas continentales, menos oxígeno profundo va con más mortalidad ambiental (Spearman): ACS17A Hualaihué ρ = −0,62 (p = 0,006), ACS16 Chaitén ρ = −0,64 (p = 0,005), ACS1 Cochamó ρ = −0,41 (p = 0,02).
- En 2026 el oxígeno profundo de ACS1 estuvo bajo 5 mg/L casi todas las horas desde enero, con mínimos cercanos a 3,3 mg/L en mayo y junio. La mortalidad ambiental de Cochamó subió a 1,45 % en julio, cuando lo habitual es menos de 0,05 %. En Hualaihué el máximo fue 1,24 % en mayo.
- En Chiloé (ACS10A, ACS11) el oxígeno casi nunca baja de 5 mg/L y no hay relación negativa: ahí la mortalidad ambiental sigue más a la temperatura (ACS10A ρ = +0,61), lo que apunta a otras causas, como floraciones de algas.
- Limitaciones: entre 17 y 42 meses por boya, una boya representa a toda una comuna y la causa "Ambiental" no distingue entre oxígeno y algas. Es una asociación, no una prueba de causalidad.
