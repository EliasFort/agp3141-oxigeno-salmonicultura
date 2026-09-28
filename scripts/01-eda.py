"""
01-eda.py
AGP3141 - Actividad semanal 4: análisis exploratorio (EDA) y datos ausentes.

Datos: boya oceanográfica ACS10A (Los Lagos, Chiloé), sistema de monitoreo
de las Agrupaciones de Concesiones de Salmonicultura del IFOP.
Fuente: API pública https://acs.ifop.cl/api/docs/public/

Uso (desde la carpeta raíz del repositorio):
    python scripts/01-eda.py

Si datos/brutos/ifop_acs10a_horario.csv no existe, el script lo descarga
de la API (necesita internet). Requiere: pandas, numpy, matplotlib.
"""

import json
import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_BRUTO = RAIZ / "datos" / "brutos" / "ifop_acs10a_horario.csv"
ARCHIVO_LIMPIO = RAIZ / "datos" / "procesados" / "acs10a_horario_validado.csv"
CARPETA_FIG = RAIZ / "figuras"

BOYA = "ACS10A"
INICIO, FIN = "2022-10-01T00:00:00", "2026-09-25T23:59:59"

# (instrumento, variable en la API, nombre de columna)
# sonda_sup = sonda superficial, sonda_prof = sonda profunda, meteo = estación meteorológica
SERIES = [
    ("sonda_sup", "water_temperature", "temp_agua_sup"),
    ("sonda_sup", "oxygen_conc", "oxigeno_mgl_sup"),
    ("sonda_sup", "oxygen_sat", "oxigeno_sat_sup"),
    ("sonda_sup", "salinity", "salinidad_sup"),
    ("sonda_sup", "ph", "ph_sup"),
    ("sonda_sup", "fluorescence", "fluorescencia_sup"),
    ("sonda_sup", "turbidity", "turbidez_sup"),
    ("sonda_prof", "water_temperature", "temp_agua_prof"),
    ("sonda_prof", "oxygen_conc", "oxigeno_mgl_prof"),
    ("sonda_prof", "salinity", "salinidad_prof"),
    ("meteo", "air_temperature", "temp_aire"),
    ("meteo", "wind_speed", "viento_ms"),
    ("meteo", "precipitation", "precipitacion_mm"),
]

# Rangos físicamente plausibles para aguas interiores de Chiloé.
# Un valor fuera de rango no es una medición real: es un dato ausente "disfrazado".
RANGOS = {
    "temp_agua_sup": (4, 20),        # °C; 0 y 26 °C son fallas del sensor
    "temp_agua_prof": (4, 20),
    "oxigeno_mgl_sup": (0.01, 20),   # mg/L; 0 exacto = sensor sin lectura
    "oxigeno_mgl_prof": (0.01, 20),
    "oxigeno_sat_sup": (0.01, 200),  # %; hay valores de 5,8e11 %
    "salinidad_sup": (15, 40),       # PSU; 0,01 = celda de conductividad sin agua o sucia
    "salinidad_prof": (15, 40),
    "ph_sup": (6.5, 9),
    "fluorescencia_sup": (0, 999),   # -1 = código de error; 1000 = sensor saturado
    "turbidez_sup": (0, 500),        # -1 = código de error
    "viento_ms": (0, 45),            # m/s; promedios horarios de 59 m/s no son reales
    "precipitacion_mm": (0, 50),     # mm/h; >50 mm en una hora no es plausible aquí
}

# Colores (paleta de referencia validada para daltonismo)
AZUL, NARANJO = "#2a78d6", "#eb6834"
TINTA, TINTA_2, GRILLA, FONDO = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"


def descargar_datos():
    """Descarga promedios horarios desde la API pública del IFOP."""
    base = "https://acs.ifop.cl/api/v1/lecturas/chart_data/"
    tablas = []
    for instrumento, variable, nombre in SERIES:
        url = (f"{base}?boya_code={BOYA}&instrument_code={instrumento}"
               f"&variable_code={variable}&time_start={INICIO}&time_end={FIN}"
               f"&interval=hourly&statistic=avg")
        with urllib.request.urlopen(url, timeout=120) as r:
            d = json.load(r)
        tablas.append(pd.Series(d["values"], index=d["times"], name=nombre))
        print(f"  {nombre}: {d['count']} registros")
    df = pd.concat(tablas, axis=1)
    df.index.name = "fecha_hora_utc"
    ARCHIVO_BRUTO.parent.mkdir(parents=True, exist_ok=True)
    df.sort_index().to_csv(ARCHIVO_BRUTO)


def estilo(ax):
    ax.set_facecolor(FONDO)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(GRILLA)
    ax.tick_params(colors=TINTA_2, labelsize=9)
    ax.grid(axis="y", color=GRILLA, linewidth=0.6)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# 1. Cargar y completar la grilla horaria
# ---------------------------------------------------------------------------
if not ARCHIVO_BRUTO.exists():
    print("Descargando datos desde la API del IFOP...")
    descargar_datos()

bruto = pd.read_csv(ARCHIVO_BRUTO, parse_dates=["fecha_hora_utc"],
                    index_col="fecha_hora_utc")

# La API solo entrega las horas con al menos un dato. Las horas en que la boya
# no transmitió nada simplemente no aparecen: hay que crearlas para verlas como NA.
horas = pd.date_range(bruto.index.min(), bruto.index.max(), freq="h")
df = bruto.reindex(horas)
df.index.name = "fecha_hora_utc"
horas_vacias = len(horas) - len(bruto)

print("=" * 70)
print(f"Boya {BOYA} | {df.index.min():%Y-%m-%d} a {df.index.max():%Y-%m-%d}")
print(f"Horas esperadas: {len(horas):,} | horas sin ningún dato: {horas_vacias:,}"
      f" ({horas_vacias / len(horas):.1%})")

# ---------------------------------------------------------------------------
# 2. Detectar valores inválidos (ausentes disfrazados)
# ---------------------------------------------------------------------------
na_original = df.isna().sum()
invalidos = pd.Series(0, index=df.columns)

for col, (minimo, maximo) in RANGOS.items():
    malos = df[col].notna() & ~df[col].between(minimo, maximo)
    invalidos[col] = malos.sum()
    df.loc[malos, col] = np.nan

# Estación meteorológica apagada: temperatura del aire Y viento exactamente en 0
apagada = (bruto.reindex(horas)["temp_aire"] == 0) & (bruto.reindex(horas)["viento_ms"] == 0)
for col in ("temp_aire", "viento_ms"):
    invalidos[col] += (apagada & df[col].notna()).sum()
    df.loc[apagada, col] = np.nan

resumen_na = pd.DataFrame({
    "NA_original": na_original,
    "invalidos": invalidos,
    "NA_total": df.isna().sum(),
    "pct_NA": (df.isna().mean() * 100).round(1),
})
print("\nDatos ausentes por variable (horas):")
print(resumen_na.to_string())

# ---------------------------------------------------------------------------
# 3. Resumen estadístico (datos validados)
# ---------------------------------------------------------------------------
print("\nResumen de variables validadas:")
print(df.describe().T[["count", "mean", "std", "min", "50%", "max"]].round(2).to_string())

ARCHIVO_LIMPIO.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(ARCHIVO_LIMPIO)

# ---------------------------------------------------------------------------
# 4. ¿Las fallas dependen de otra variable observada? (pista de MAR)
# ---------------------------------------------------------------------------
local = df.tz_convert("America/Santiago")
diario = local.resample("D").mean()
na_diario = local.isna().resample("D").mean()

ventoso = diario["viento_ms"] >= diario["viento_ms"].quantile(0.9)
print("\n% de horas sin oxígeno superficial según el viento del día:")
for etiqueta, grupo in (("días más ventosos (10%)", ventoso),
                        ("resto de los días", ~ventoso & diario["viento_ms"].notna())):
    print(f"  {etiqueta:<25} {na_diario.loc[grupo, 'oxigeno_mgl_sup'].mean():.1%}")

# Ausencias cortas (transmisión) vs. largas (mantención o retiro de la sonda)
def tramos(serie_na):
    grupos = (serie_na != serie_na.shift()).cumsum()
    largos = serie_na.groupby(grupos).agg(["first", "size"])
    return largos.loc[largos["first"], "size"]

t = tramos(df["oxigeno_mgl_sup"].isna())
print(f"\nTramos sin oxígeno superficial: {len(t)} | de 1-2 horas: {(t <= 2).sum()}"
      f" | de más de 7 días: {(t > 168).sum()} (suman {t[t > 168].sum():,} horas)")

# ---------------------------------------------------------------------------
# 5. Figuras
# ---------------------------------------------------------------------------
CARPETA_FIG.mkdir(exist_ok=True)
plt.rcParams["font.family"] = "DejaVu Sans"

# 5a. Temperatura y oxígeno diarios, superficie vs. fondo
fig, ejes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True, facecolor=FONDO)
paneles = [("temp_agua", "Temperatura del agua (°C)"),
           ("oxigeno_mgl", "Oxígeno disuelto (mg/L)")]
for ax, (var, titulo) in zip(ejes, paneles):
    estilo(ax)
    ax.plot(diario.index, diario[f"{var}_sup"], color=AZUL, lw=1.4, label="Sonda superficial")
    ax.plot(diario.index, diario[f"{var}_prof"], color=NARANJO, lw=1.4, label="Sonda profunda")
    ax.set_title(titulo, loc="left", fontsize=11, color=TINTA)
ejes[0].legend(frameon=False, fontsize=9, loc="upper left", ncol=2, labelcolor=TINTA_2)
fig.suptitle(f"Boya {BOYA} (Chiloé): promedios diarios. Los cortes en la línea son días sin datos.",
             x=0.01, ha="left", fontsize=12, color=TINTA)
fig.tight_layout()
fig.savefig(CARPETA_FIG / "01-temperatura-oxigeno-diario.png", dpi=150, facecolor=FONDO)
plt.close(fig)

# 5b. Porcentaje de horas sin dato por mes y variable
mensual = local.isna().resample("MS").mean().T * 100
fig, ax = plt.subplots(figsize=(12, 5), facecolor=FONDO)
azules = plt.matplotlib.colors.LinearSegmentedColormap.from_list(
    "azules", ["#fcfcfb", "#cde2fb", "#86b6ef", "#2a78d6", "#1c5cab", "#0d366b"])
im = ax.imshow(mensual.values, aspect="auto", cmap=azules, vmin=0, vmax=100)
ax.set_yticks(range(len(mensual.index)), mensual.index, fontsize=9, color=TINTA_2)
meses = mensual.columns
marcas = [i for i, m in enumerate(meses) if m.month in (1, 7)]
nombre_mes = {1: "ene", 7: "jul"}
ax.set_xticks(marcas, [f"{nombre_mes[meses[i].month]} {meses[i].year}" for i in marcas],
              fontsize=9, color=TINTA_2)
for lado in ax.spines.values():
    lado.set_visible(False)
barra = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
barra.set_label("% de horas sin dato válido", color=TINTA_2, fontsize=9)
barra.outline.set_visible(False)
barra.ax.tick_params(colors=TINTA_2, labelsize=9)
ax.set_title(f"Datos ausentes por mes, boya {BOYA} (incluye valores inválidos convertidos a NA)",
             loc="left", fontsize=12, color=TINTA)
fig.tight_layout()
fig.savefig(CARPETA_FIG / "02-datos-ausentes-por-mes.png", dpi=150, facecolor=FONDO)
plt.close(fig)

print(f"\nFiguras guardadas en {CARPETA_FIG}")
