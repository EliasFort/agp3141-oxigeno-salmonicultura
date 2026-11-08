# agp3141-oxigeno-salmonicultura

Proyecto final del curso AGP3141 *Visualización y Análisis de Datos Medioambientales* (MAGEA, UC).

**Pregunta:** ¿qué condiciones del agua (temperatura, oxígeno disuelto, salinidad) anteceden a los episodios de mortalidad de salmones en Los Lagos?

## La historia hasta ahora

Los salmones de cultivo necesitan agua con suficiente oxígeno. En Los Lagos, el IFOP mantiene boyas junto a las agrupaciones de concesiones de salmonicultura (ACS) que miden el agua cada hora. Este proyecto usa las 5 boyas de la región para responder tres preguntas exploratorias:

1. **¿Dónde y cuándo baja el oxígeno?** El estuario de Reloncaví (ACS1) tiene el agua profunda más pobre en oxígeno de las cinco boyas (mediana de 5,1 mg/L). Entre marzo y julio de 2026 pasó más de 130 días bajo 4 mg/L.
2. **¿La temperatura explica el oxígeno?** Solo en Reloncaví hay una relación clara: cada grado más de temperatura profunda se asocia con unos 1,9 mg/L menos de oxígeno (R² = 0,40). En las boyas de Chiloé la temperatura explica casi nada (R² < 0,07).
3. **¿Esos episodios coinciden con la mortalidad?** En las boyas del continente, sí. Los meses con menos oxígeno profundo tienen más mortalidad por causa ambiental (Spearman): Hualaihué ρ = −0,62 (p = 0,006), Chaitén ρ = −0,64 (p = 0,005) y Cochamó ρ = −0,41 (p = 0,02). En 2026 el oxígeno profundo de Reloncaví bajó a cerca de 3,3 mg/L y la mortalidad ambiental de Cochamó llegó a 1,45 % de los peces en julio, cuando lo habitual es menos de 0,05 %. En Chiloé, donde el oxígeno casi nunca baja de 5 mg/L, no aparece esa relación.

## Datos

| Fuente | Contenido | Estado |
|---|---|---|
| IFOP, sistema de monitoreo de las ACS ([API pública](https://acs.ifop.cl/api/docs/public/)) | 5 boyas de Los Lagos: promedios horarios de 13 variables (`datos/brutos/ifop_<boya>_horario.csv`) | Descargado |
| Sernapesca, vía Ley de Transparencia (solicitud AH010T0009768, ORD. DN-05691/2026) | Mortalidad semanal de salmónidos por comuna, especie y causa (ene 2017 a sept 2026) y existencias mensuales por comuna (hasta ago 2026), en `datos/brutos/sernapesca/` | Recibido. El Excel de mortalidad pesa ~200 MB y no se sube a GitHub; su versión agregada está en `datos/procesados/` |
| Hecho a mano | Zona de cada boya (`datos/brutos/boyas_metadata.csv`) | Listo |

La columna `boya` es la llave que une las tablas de las boyas. Pedí la mortalidad por agrupación de concesiones, pero Sernapesca la entregó por comuna. Por eso cada boya se asigna a la comuna donde está instalada: ACS1 → Cochamó, ACS17A → Hualaihué, ACS16 → Chaitén, ACS10A → Puqueldón y ACS11 → Queilén.

### Boyas (de norte a sur)

| Boya | Zona | Datos desde | Horas con datos válidos |
|---|---|---|---|
| ACS1 | Estuario de Reloncaví | dic 2023 | 94 % |
| ACS16 | Golfo de Ancud, costa continental | dic 2024 | 69 % |
| ACS17A | Hornopirén | dic 2024 | 85 % |
| ACS10A | Chiloé central | nov 2022 | 88 % |
| ACS11 | Sur de Chiloé | dic 2024 | 94 % |

## Estructura

```
agp3141-oxigeno-salmonicultura/
├── datos/
│   ├── brutos/          # tal como vienen de la fuente; no se editan
│   └── procesados/      # generados por los scripts (se pueden borrar y regenerar)
├── scripts/
│   ├── 01-eda.py                # EDA y datos ausentes de la ACS10A
│   ├── 02-limpieza-boyas.py     # limpia las 5 boyas, las une y pasa a formato largo
│   ├── 03-modelos-por-boya.py   # un modelo lineal por boya y por estación
│   ├── 04-diccionario-validacion.py      # diccionario de datos y función de validación
│   ├── 05-sernapesca.py                  # lee los Excel de Sernapesca y los pasa a CSV
│   └── 06-cruce-boyas-mortalidad.py      # oxígeno de cada boya vs. mortalidad de su comuna
├── informe/
│   └── informe.qmd              # informe en Quarto con los tres hallazgos
├── figuras/
├── requirements.txt
└── README.md
```

## Cómo reproducir

```
pip install -r requirements.txt
python scripts/01-eda.py
python scripts/02-limpieza-boyas.py
python scripts/03-modelos-por-boya.py
python scripts/04-diccionario-validacion.py
python scripts/05-sernapesca.py
python scripts/06-cruce-boyas-mortalidad.py
quarto render informe/informe.qmd
```

Los scripts se corren en orden desde la carpeta raíz. Cada uno lee solo de `datos/` y escribe en `datos/procesados/` y `figuras/`. El script 05 necesita los Excel de Sernapesca en `datos/brutos/sernapesca/`; como el de mortalidad no está en GitHub, quien clone el repositorio puede saltarse ese paso, porque sus resultados ya están en `datos/procesados/`. El informe necesita [Quarto](https://quarto.org).

## Decisiones de limpieza

- La API entrega solo las horas con algún dato. Las horas vacías se recrean para que queden como NA.
- Los valores físicamente imposibles (por ejemplo, oxígeno de 6.527 mg/L o agua a 33 °C) se convierten a NA. Los rangos están al inicio de `02-limpieza-boyas.py`.
- En las boyas de la costa continental (ACS1, ACS16 y ACS17A) se acepta salinidad superficial desde 1 PSU, porque reciben agua de ríos. En Chiloé el mínimo es 15 PSU.
- En la ACS17A los primeros 19 días (30 dic 2024 al 17 ene 2025) tienen temperaturas profundas de 15 °C, que no calzan con el resto de la serie. Probablemente corresponden a la instalación de la boya. Siguen en `datos/procesados/`, pero el informe los excluye. Por eso el modelo de `03-modelos-por-boya.py` da R² = 0,32 en ACS17A, y sin esos días la relación prácticamente desaparece.
- Mortalidad: tasa mensual = peces muertos por causa *Ambiental* / existencias de la comuna ese mes × 100. Las semanas que cruzan dos meses se reparten según sus días.

## Limitaciones del hallazgo 3

- Hay pocos meses por boya: entre 17 y 42.
- Una boya representa a toda su comuna.
- La causa "Ambiental" no separa la falta de oxígeno de las floraciones de algas.
- Es una asociación, no una prueba de que el oxígeno cause la mortalidad.

## Uso de IA

Usé Claude (Anthropic) para buscar fuentes de datos, redactar la solicitud a Sernapesca, escribir y revisar el código de los scripts, y ordenar los textos. Las preguntas, la elección de datos y la interpretación de los resultados son mías.
