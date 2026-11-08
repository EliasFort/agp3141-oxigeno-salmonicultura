"""
02-limpieza-boyas.py
AGP3141 - Limpieza de las 5 boyas IFOP de Los Lagos y unión en una sola tabla.

Aplica a cada boya la misma limpieza que 01-eda.py hizo con la ACS10A, pero con
una función (en vez de copiar el código cinco veces) y con rangos ajustados a
cada zona. Luego pasa los datos a formato largo (una fila por boya, día y
variable), que es el formato cómodo para graficar por boya.

Uso (desde la carpeta raíz del repositorio):
    python scripts/02-limpieza-boyas.py

Entradas:
    datos/brutos/ifop_<boya>_horario.csv   (descargados de la API del IFOP)
    datos/brutos/boyas_metadata.csv        (zona de cada boya, hecho a mano)
Salidas:
    datos/procesados/boyas_horario_validado.csv   (horario, ancho, con columna boya)
    datos/procesados/boyas_diario.csv             (promedios diarios, ancho)
    datos/procesados/boyas_diario_largo.csv       (promedios diarios, largo)
    figuras/03-oxigeno-profundo-por-boya.png
Requiere: pandas, numpy, matplotlib.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "datos" / "brutos"
PROCESADOS = RAIZ / "datos" / "procesados"
FIGURAS = RAIZ / "figuras"

# Rangos físicamente plausibles (valor mínimo, valor máximo).
# Un valor fuera de rango es una falla del sensor, no una medición: pasa a NA.
RANGOS = {
    "temp_agua_sup": (4, 22),        # °C; hay 0, -1,7 y 32,9 °C que son fallas
    "temp_agua_prof": (4, 22),
    "oxigeno_mgl_sup": (0.01, 20),   # mg/L; 0 exacto = sensor sin lectura; 6.527 mg/L no existe
    "oxigeno_mgl_prof": (0.01, 20),
    "oxigeno_sat_sup": (0.01, 200),  # %; hay valores de 5,8e11 %
    "salinidad_sup": (15, 40),       # PSU; 0 = celda de conductividad sin agua o sucia
    "salinidad_prof": (15, 40),
    "ph_sup": (6.5, 9),
    "fluorescencia_sup": (0, 999),   # -1 = código de error; 1000 = sensor saturado
    "turbidez_sup": (0, 500),        # -1 = código de error
    "viento_ms": (0, 45),            # m/s
    "precipitacion_mm": (0, 50),     # mm/h
}

# Excepciones por zona. Las boyas de la costa continental reciben agua de ríos:
# en Reloncaví (ACS1) el 5 % de las horas tiene salinidad superficial bajo 9 PSU,
# y eso es agua dulce real, no un error. Ahí solo se descarta el 0 exacto.
EXCEPCIONES = {
    "ACS1": {"salinidad_sup": (1, 40)},
    "ACS16": {"salinidad_sup": (1, 40)},
    "ACS17A": {"salinidad_sup": (1, 40)},
}

BOYAS = ["ACS1", "ACS16", "ACS17A", "ACS10A", "ACS11"]  # de norte a sur

# Colores (paleta validada para daltonismo)
TINTA, TINTA_2, GRILLA, FONDO = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
AZUL = "#2a78d6"


def limpiar_boya(codigo):
    """Lee una boya, completa la grilla horaria y convierte valores imposibles a NA.

    Devuelve la tabla limpia y un resumen de cuántos datos se perdieron.
    """
    archivo = BRUTOS / f"ifop_{codigo.lower()}_horario.csv"
    if not archivo.exists():
        raise FileNotFoundError(f"No encuentro {archivo}. ¿Descargaste la boya {codigo}?")

    bruto = pd.read_csv(archivo, parse_dates=["fecha_hora_utc"], index_col="fecha_hora_utc")

    # La API solo entrega horas con al menos un dato: las horas vacías hay que crearlas.
    horas = pd.date_range(bruto.index.min(), bruto.index.max(), freq="h")
    df = bruto.reindex(horas)
    df.index.name = "fecha_hora_utc"

    rangos = {**RANGOS, **EXCEPCIONES.get(codigo, {})}
    invalidos = 0
    for col, (minimo, maximo) in rangos.items():
        malos = df[col].notna() & ~df[col].between(minimo, maximo)
        invalidos += malos.sum()
        df.loc[malos, col] = np.nan

    # Estación meteorológica apagada: temperatura del aire y viento exactamente en 0
    apagada = (df["temp_aire"] == 0) & (df["viento_ms"] == 0)
    invalidos += 2 * apagada.sum()
    df.loc[apagada, ["temp_aire", "viento_ms"]] = np.nan

    resumen = {
        "boya": codigo,
        "desde": df.index.min().strftime("%Y-%m-%d"),
        "hasta": df.index.max().strftime("%Y-%m-%d"),
        "horas": len(horas),
        "horas_sin_transmision": len(horas) - len(bruto),
        "valores_invalidos": int(invalidos),
        "pct_NA_final": round(df.isna().to_numpy().mean() * 100, 1),
    }
    df.insert(0, "boya", codigo)
    return df.reset_index(), resumen


# ---------------------------------------------------------------------------
# 1. Limpiar las 5 boyas con la misma función y unirlas
# ---------------------------------------------------------------------------
resultados = [limpiar_boya(b) for b in BOYAS]
horario = pd.concat([tabla for tabla, _ in resultados], ignore_index=True)
resumen = pd.DataFrame([r for _, r in resultados])

print("=" * 78)
print("Limpieza de las boyas IFOP de Los Lagos")
print("=" * 78)
print(resumen.to_string(index=False))

# ---------------------------------------------------------------------------
# 2. Unir con la tabla de metadatos (join por la columna ID 'boya')
# ---------------------------------------------------------------------------
metadata = pd.read_csv(BRUTOS / "boyas_metadata.csv", dtype=str)

# Revisión previa (equivale a anti_join): ¿hay boyas en los datos sin metadatos?
sin_metadata = set(horario["boya"]) - set(metadata["boya"])
if sin_metadata:
    raise ValueError(f"Boyas sin fila en boyas_metadata.csv: {sin_metadata}")

# ---------------------------------------------------------------------------
# 3. Promedios diarios (hora de Chile) y formato largo
# ---------------------------------------------------------------------------
horario["fecha"] = (horario["fecha_hora_utc"].dt.tz_convert("America/Santiago")
                    .dt.tz_localize(None).dt.normalize())
diario = (horario.drop(columns="fecha_hora_utc")
          .groupby(["boya", "fecha"]).mean().reset_index())
diario = diario.merge(metadata[["boya", "zona"]], on="boya", how="left")  # left_join

# Formato largo: una fila por boya, día y variable (equivale a pivot_longer).
# Los nombres de columna siguen el patrón <variable>_<nivel>, por ejemplo
# temp_agua_sup o oxigeno_mgl_prof. Se separan en el ÚLTIMO guion bajo, con
# la misma idea que names_pattern = "(.*)_([a-z]+)$" en R.
medidas = [c for c in diario.columns if c.endswith(("_sup", "_prof"))]
largo = diario.melt(id_vars=["boya", "zona", "fecha"], value_vars=medidas,
                    var_name="columna", value_name="valor").dropna(subset=["valor"])
largo[["variable", "nivel"]] = largo["columna"].str.extract(r"^(.*)_([a-z]+)$")
largo = largo.drop(columns="columna")[["boya", "zona", "fecha", "variable", "nivel", "valor"]]

PROCESADOS.mkdir(parents=True, exist_ok=True)
horario.drop(columns="fecha").to_csv(PROCESADOS / "boyas_horario_validado.csv", index=False)
diario.to_csv(PROCESADOS / "boyas_diario.csv", index=False)
largo.to_csv(PROCESADOS / "boyas_diario_largo.csv", index=False)

print(f"\nFilas: horario {len(horario):,} | diario {len(diario):,} | diario largo {len(largo):,}")
print("\nMediana diaria por boya (datos validados):")
cols = ["temp_agua_sup", "oxigeno_mgl_sup", "oxigeno_mgl_prof", "salinidad_sup"]
print(diario.groupby("boya")[cols].median().reindex(BOYAS).round(2).to_string())

# ---------------------------------------------------------------------------
# 4. Figura: oxígeno profundo diario, un panel por boya (desde el formato largo)
# ---------------------------------------------------------------------------
FIGURAS.mkdir(exist_ok=True)
plt.rcParams["font.family"] = "DejaVu Sans"
ox = largo[(largo["variable"] == "oxigeno_mgl") & (largo["nivel"] == "prof")]
inicio, fin = ox["fecha"].min(), ox["fecha"].max()

fig, ejes = plt.subplots(len(BOYAS), 1, figsize=(11, 9), sharex=True, sharey=True,
                         facecolor=FONDO)
for ax, codigo in zip(ejes, BOYAS):
    serie = ox[ox["boya"] == codigo].set_index("fecha")["valor"]
    serie = serie.reindex(pd.date_range(inicio, fin, freq="D"))  # cortes visibles
    ax.set_facecolor(FONDO)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(GRILLA)
    ax.tick_params(colors=TINTA_2, labelsize=9)
    ax.grid(axis="y", color=GRILLA, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.axhline(4, color=TINTA_2, lw=0.8, ls="--")
    ax.plot(serie.index, serie.values, color=AZUL, lw=1.2)
    zona = metadata.set_index("boya").loc[codigo, "zona"]
    ax.set_title(f"{codigo} · {zona}", loc="left", fontsize=10, color=TINTA)
ejes[0].text(1.0, 1.02, "línea punteada: 4 mg/L", transform=ejes[0].transAxes,
             ha="right", va="bottom", fontsize=8, color=TINTA_2)
fig.suptitle("Oxígeno disuelto en la sonda profunda (mg/L, promedio diario), de norte a sur",
             x=0.01, ha="left", fontsize=12, color=TINTA)
fig.tight_layout()
fig.savefig(FIGURAS / "03-oxigeno-profundo-por-boya.png", dpi=150, facecolor=FONDO)
plt.close(fig)
print(f"\nFigura guardada en {FIGURAS / '03-oxigeno-profundo-por-boya.png'}")
