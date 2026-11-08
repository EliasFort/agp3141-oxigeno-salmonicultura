"""
03-modelos-por-boya.py
AGP3141 - Actividad semanal 9: un modelo por grupo (group_by + nest + map en R).

Pregunta: ¿en qué boyas el oxígeno del agua profunda depende de la temperatura?
El agua más cálida disuelve menos oxígeno, así que esperaríamos una pendiente
negativa. Pero si en una zona influyen más otras cosas (corrientes, ríos, algas),
la temperatura explicará poco (R² bajo).

Equivalencias con lo visto en clase (R -> Python):
    group_by() + nest()   ->  df.groupby(...)
    map(lm)               ->  .apply(ajustar_lineal)
    tidy() / glance()     ->  columnas intercepto, pendiente, r2 y n que devuelve la función
    augment()             ->  columnas oxigeno_predicho y residuo
    slice_min()           ->  .nsmallest()

Uso (desde la raíz del repo, después de 02-limpieza-boyas.py):
    python scripts/03-modelos-por-boya.py
Requiere: pandas, numpy, matplotlib (el modelo lineal se ajusta con numpy).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DIARIO = RAIZ / "datos" / "procesados" / "boyas_diario.csv"
SALIDA = RAIZ / "datos" / "procesados"
FIGURAS = RAIZ / "figuras"

X, Y = "temp_agua_prof", "oxigeno_mgl_prof"
BOYAS = ["ACS1", "ACS16", "ACS17A", "ACS10A", "ACS11"]  # de norte a sur
ESTACIONES = ["verano", "otoño", "invierno", "primavera"]
MIN_DIAS = 30  # con menos días el modelo no es confiable

TINTA, TINTA_2, GRILLA, FONDO = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
AZUL, NARANJO = "#2a78d6", "#eb6834"


def ajustar_lineal(grupo, x=X, y=Y):
    """Ajusta y = intercepto + pendiente * x a un grupo y devuelve el resumen del modelo.

    Es el equivalente a lm() + tidy() + glance(): coeficientes, R² y número de días.
    """
    datos = grupo[[x, y]].dropna()
    if len(datos) < MIN_DIAS:
        return pd.Series({"n": len(datos), "intercepto": np.nan,
                          "pendiente": np.nan, "r2": np.nan})
    pendiente, intercepto = np.polyfit(datos[x], datos[y], 1)
    r2 = np.corrcoef(datos[x], datos[y])[0, 1] ** 2
    return pd.Series({"n": len(datos), "intercepto": intercepto,
                      "pendiente": pendiente, "r2": r2})


def estilo(ax):
    ax.set_facecolor(FONDO)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(GRILLA)
    ax.tick_params(colors=TINTA_2, labelsize=9)
    ax.grid(color=GRILLA, linewidth=0.6)
    ax.set_axisbelow(True)


diario = pd.read_csv(DIARIO, parse_dates=["fecha"])
mes_a_estacion = {12: "verano", 1: "verano", 2: "verano", 3: "otoño", 4: "otoño",
                  5: "otoño", 6: "invierno", 7: "invierno", 8: "invierno",
                  9: "primavera", 10: "primavera", 11: "primavera"}
diario["estacion"] = diario["fecha"].dt.month.map(mes_a_estacion)

# ---------------------------------------------------------------------------
# 1. Un modelo por boya (5 modelos)
# ---------------------------------------------------------------------------
por_boya = (diario.groupby("boya").apply(ajustar_lineal, include_groups=False)
            .reindex(BOYAS))
por_boya["n"] = por_boya["n"].astype(int)

print("=" * 72)
print(f"Modelo por boya: {Y} ~ {X} (promedios diarios)")
print("=" * 72)
print(por_boya.round(3).to_string())

# ---------------------------------------------------------------------------
# 2. Un modelo por boya y estación del año (hasta 20 modelos)
# ---------------------------------------------------------------------------
por_estacion = (diario.groupby(["boya", "estacion"])
                .apply(ajustar_lineal, include_groups=False).reset_index())
por_estacion["n"] = por_estacion["n"].astype(int)

print(f"\nModelos por boya y estación: {len(por_estacion)}")
print("Los 5 con menor R² (slice_min):")
print(por_estacion.nsmallest(5, "r2").round(3).to_string(index=False))
print("Los 5 con mayor R²:")
print(por_estacion.nlargest(5, "r2").round(3).to_string(index=False))

# ---------------------------------------------------------------------------
# 3. augment(): oxígeno predicho y residuo de cada día, con el modelo de su boya
# ---------------------------------------------------------------------------
diario = diario.merge(por_boya[["intercepto", "pendiente"]], left_on="boya",
                      right_index=True, how="left")
diario["oxigeno_predicho"] = diario["intercepto"] + diario["pendiente"] * diario[X]
diario["residuo"] = diario[Y] - diario["oxigeno_predicho"]

print("\nACS1: días con MENOS oxígeno del esperado según su temperatura (residuo más negativo):")
acs1 = diario[diario["boya"] == "ACS1"].dropna(subset=["residuo"])
peores = acs1.nsmallest(5, "residuo")[["fecha", X, Y, "oxigeno_predicho", "residuo"]]
print(peores.round({X: 2, Y: 2, "oxigeno_predicho": 2, "residuo": 2}).to_string(index=False))

SALIDA.mkdir(parents=True, exist_ok=True)
por_boya.round(4).to_csv(SALIDA / "modelos_por_boya.csv")
por_estacion.round(4).to_csv(SALIDA / "modelos_por_boya_estacion.csv", index=False)
(diario[["boya", "fecha", X, Y, "oxigeno_predicho", "residuo"]]
 .dropna(subset=["residuo"]).round({X: 3, Y: 3, "oxigeno_predicho": 3, "residuo": 3})
 .to_csv(SALIDA / "residuos_oxigeno_por_boya.csv", index=False))

# ---------------------------------------------------------------------------
# 4. Figura: oxígeno vs temperatura, un panel por boya, con su recta
# ---------------------------------------------------------------------------
FIGURAS.mkdir(exist_ok=True)
plt.rcParams["font.family"] = "DejaVu Sans"

fig, ejes = plt.subplots(1, len(BOYAS), figsize=(14, 3.8), sharex=True, sharey=True,
                         facecolor=FONDO)
for ax, codigo in zip(ejes, BOYAS):
    estilo(ax)
    g = diario[diario["boya"] == codigo].dropna(subset=[X, Y])
    m = por_boya.loc[codigo]
    ax.scatter(g[X], g[Y], s=6, color=AZUL, alpha=0.35, linewidths=0)
    xs = np.linspace(g[X].min(), g[X].max(), 50)
    ax.plot(xs, m["intercepto"] + m["pendiente"] * xs, color=NARANJO, lw=2)
    ax.set_title(codigo, loc="left", fontsize=11, color=TINTA)
    ax.text(0.03, 0.04, f"R² = {m['r2']:.2f}\npendiente = {m['pendiente']:+.2f}",
            transform=ax.transAxes, fontsize=9, color=TINTA_2, va="bottom")
    ax.set_xlabel("Temperatura profunda (°C)", fontsize=9, color=TINTA_2)
ejes[0].set_ylabel("Oxígeno profundo (mg/L)", fontsize=9, color=TINTA_2)
fig.suptitle("Solo en el estuario de Reloncaví (ACS1) el agua más cálida trae claramente "
             "menos oxígeno", x=0.01, ha="left", fontsize=12, color=TINTA)
fig.tight_layout()
fig.savefig(FIGURAS / "04-oxigeno-vs-temperatura-por-boya.png", dpi=150, facecolor=FONDO)
plt.close(fig)

# ---------------------------------------------------------------------------
# 5. Figura: R² de los 20 modelos (boya x estación)
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 4), facecolor=FONDO)
estilo(ax)
ax.grid(axis="y", visible=False)
for i, codigo in enumerate(BOYAS):
    g = por_estacion[por_estacion["boya"] == codigo].set_index("estacion").reindex(ESTACIONES)
    negativa = g["pendiente"] < 0
    ax.scatter(g.loc[negativa, "r2"], [i] * negativa.sum(), s=70, color=NARANJO,
               label="pendiente negativa" if i == 0 else None, zorder=3)
    ax.scatter(g.loc[~negativa, "r2"], [i] * (~negativa).sum(), s=70, facecolors="none",
               edgecolors=AZUL, linewidths=1.6,
               label="pendiente positiva" if i == 0 else None, zorder=3)
    # etiquetas alternadas arriba/abajo para que no se tapen cuando los R² están cerca
    for k, (est, fila) in enumerate(g.dropna(subset=["r2"]).sort_values("r2").iterrows()):
        arriba = k % 2 == 0
        ax.annotate(est[:3], (fila["r2"], i), xytext=(0, 8 if arriba else -14),
                    textcoords="offset points", ha="center", fontsize=7, color=TINTA_2)
ax.set_yticks(range(len(BOYAS)), BOYAS)
ax.invert_yaxis()
ax.set_xlim(0, 1)
ax.set_xlabel("R² (cuánto de la variación del oxígeno explica la temperatura)",
              fontsize=9, color=TINTA_2)
ax.legend(frameon=False, fontsize=8, loc="lower right", labelcolor=TINTA_2)
ax.set_title("R² de 20 modelos: oxígeno profundo ~ temperatura profunda, por boya y estación",
             loc="left", fontsize=11, color=TINTA)
fig.tight_layout()
fig.savefig(FIGURAS / "05-r2-por-boya-y-estacion.png", dpi=150, facecolor=FONDO)
plt.close(fig)

print(f"\nTablas en {SALIDA} y figuras en {FIGURAS}")
