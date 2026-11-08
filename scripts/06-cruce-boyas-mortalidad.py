"""
06-cruce-boyas-mortalidad.py
AGP3141 - Proyecto final, hallazgo 3: ¿el oxígeno bajo se asocia con más mortalidad?

Une, mes a mes, las condiciones medidas por cada boya del IFOP con la tasa de
mortalidad de salmónidos de la comuna donde está la boya (datos de Sernapesca).

  tasa de mortalidad (%) = peces muertos en el mes / existencias del mes x 100

Se usa la causa "Ambiental" (la que Sernapesca asigna a eventos de oxígeno, algas,
temperatura) y también la mortalidad total.

Supuestos y limitaciones:
  - Sernapesca entregó los datos por comuna, no por agrupación de concesiones, así
    que cada boya representa a toda su comuna (ver BOYA_COMUNA).
  - Las semanas que cruzan dos meses se reparten entre ambos según sus días.
  - Solo se usan meses con al menos 15 días de datos de oxígeno superficial.
  - Con 17 a 42 meses por boya, las correlaciones son exploratorias.

Requiere haber corrido 02-limpieza-boyas.py y 05-sernapesca.py. Uso: python scripts/06-cruce-boyas-mortalidad.py
Requiere: pandas, numpy, matplotlib, scipy.
"""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

RAIZ = Path(__file__).resolve().parent.parent
PROCESADOS = RAIZ / "datos" / "procesados"
CARPETA_FIG = RAIZ / "figuras"

# Comuna de cada boya según sus coordenadas (API del IFOP, /api/v1/boyas/)
BOYA_COMUNA = {
    "acs1": "Cochamó",      # -41,60 / -72,33  estuario de Reloncaví
    "acs10a": "Puqueldón",  # -42,65 / -73,54  este de isla Lemuy, Chiloé central
    "acs11": "Queilén",     # -42,92 / -73,59  sur de Chiloé
    "acs16": "Chaitén",     # -42,36 / -72,78  Ayacara, golfo de Ancud continental
    "acs17a": "Hualaihué",  # -42,29 / -72,46  fiordo Comau, sector Hornopirén
}
UMBRAL_HIPOXIA = 5.0  # mg/L; bajo este nivel el salmón empieza a estresarse


AZUL, NARANJO = "#2a78d6", "#eb6834"
TINTA, TINTA_2, GRILLA, FONDO = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"


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
# 1. Mortalidad mensual por comuna (Los Lagos)
# ---------------------------------------------------------------------------
mort = pd.read_csv(PROCESADOS / "sernapesca_mortalidad_semanal_comuna.csv",
                   parse_dates=["fecha_inicio", "fecha_fin"])
mort = mort[mort.region == 10]
VARS = ["mort_total", "ambiental"]

partes = []
for (ini, fin), g in mort.groupby(["fecha_inicio", "fecha_fin"]):
    dias = pd.date_range(ini, fin)
    fraccion = pd.Series(1, index=dias).groupby([dias.year, dias.month]).sum() / len(dias)
    for (anio, mes), f in fraccion.items():
        p = g[["comuna"] + VARS].copy()
        p[VARS] *= f
        p["anio"], p["mes"] = anio, mes
        partes.append(p)
mort_mes = pd.concat(partes).groupby(["comuna", "anio", "mes"])[VARS].sum().reset_index()

exis = pd.read_csv(PROCESADOS / "sernapesca_existencias_mensual_comuna.csv")
exis = (exis[exis.region == 10].groupby(["comuna", "anio", "mes"])
        .unidades.sum(min_count=1).reset_index())
mort_mes = mort_mes.merge(exis, on=["comuna", "anio", "mes"], how="inner")
mort_mes = mort_mes[mort_mes.unidades > 0]
mort_mes["tasa_total"] = mort_mes.mort_total / mort_mes.unidades * 100
mort_mes["tasa_ambiental"] = mort_mes.ambiental / mort_mes.unidades * 100

# ---------------------------------------------------------------------------
# 2. Indicadores mensuales de cada boya
# ---------------------------------------------------------------------------
def pct_bajo_umbral(s):
    s = s.dropna()
    return (s < UMBRAL_HIPOXIA).mean() * 100 if len(s) else np.nan


# Datos horarios ya validados por 02-limpieza-boyas.py
horario = pd.read_csv(PROCESADOS / "boyas_horario_validado.csv", parse_dates=["fecha_hora_utc"])
horario["boya"] = horario.boya.str.lower()

boyas = []
for boya, comuna in BOYA_COMUNA.items():
    x = horario[horario.boya == boya].set_index("fecha_hora_utc")
    x.index = x.index.tz_convert("America/Santiago")
    g = x.groupby([x.index.year, x.index.month])
    r = pd.DataFrame({
        "temp_sup": g.temp_agua_sup.mean(),
        "oxigeno_sup": g.oxigeno_mgl_sup.mean(),
        "oxigeno_prof": g.oxigeno_mgl_prof.mean(),
        "pct_horas_hipoxia_sup": g.oxigeno_mgl_sup.apply(pct_bajo_umbral),
        "pct_horas_hipoxia_prof": g.oxigeno_mgl_prof.apply(pct_bajo_umbral),
        "horas_con_oxigeno": g.oxigeno_mgl_sup.count(),
    })
    r.index.names = ["anio", "mes"]
    r = r.reset_index()
    r["boya"], r["comuna"] = boya.upper(), comuna
    boyas.append(r)
boyas = pd.concat(boyas)

cruce = boyas.merge(mort_mes, on=["comuna", "anio", "mes"], how="inner")
cruce = cruce[cruce.horas_con_oxigeno >= 15 * 24]
cruce["fecha"] = pd.to_datetime(dict(year=cruce.anio, month=cruce.mes, day=15))
cruce.to_csv(PROCESADOS / "cruce_mensual_boya_comuna.csv", index=False)

# ---------------------------------------------------------------------------
# 3. Correlaciones de Spearman (no asume relación lineal ni normalidad)
# ---------------------------------------------------------------------------
filas = []
for boya, g in cruce.groupby("boya"):
    for var in ["temp_sup", "oxigeno_sup", "oxigeno_prof", "pct_horas_hipoxia_prof"]:
        for tasa in ["tasa_ambiental", "tasa_total"]:
            d = g[[var, tasa]].dropna()
            if len(d) < 6 or d[var].nunique() < 2:
                continue
            rho, p = spearmanr(d[var], d[tasa])
            filas.append({"boya": boya, "comuna": g.comuna.iloc[0], "variable": var,
                          "tasa": tasa, "n_meses": len(d), "rho": round(rho, 2), "p": round(p, 4)})
corr = pd.DataFrame(filas)
corr.to_csv(PROCESADOS / "correlaciones_boya_mortalidad.csv", index=False)
print(corr[corr.tasa == "tasa_ambiental"].pivot(index="boya", columns="variable", values="rho"))

# ---------------------------------------------------------------------------
# 4. Figura 06: serie de tiempo en las dos boyas con hipoxia profunda
# ---------------------------------------------------------------------------
SERIES = [("ACS1", "Cochamó (ACS1, Reloncaví)", AZUL),
          ("ACS17A", "Hualaihué (ACS17A, Comau)", NARANJO)]
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.6), sharex=True, facecolor=FONDO)
for boya, etiqueta, color in SERIES:
    g = cruce[cruce.boya == boya].set_index("fecha").sort_index()
    meses = pd.date_range(g.index.min(), g.index.max(), freq="MS") + pd.Timedelta(days=14)
    g = g.reindex(meses).rename_axis("fecha").reset_index()  # meses sin datos cortan la línea
    ax1.plot(g.fecha, g.oxigeno_prof, color=color, lw=2, marker="o", ms=4, label=etiqueta)
    ax2.plot(g.fecha, g.tasa_ambiental, color=color, lw=2, marker="o", ms=4, label=etiqueta)
ax1.axhline(UMBRAL_HIPOXIA, color=TINTA_2, lw=1, ls="--")
inicio = cruce[cruce.boya.isin(["ACS1", "ACS17A"])].fecha.min()
ax1.text(inicio, UMBRAL_HIPOXIA - 0.12, "  umbral de hipoxia, 5 mg/L",
         color=TINTA_2, fontsize=8.5, va="top")
ax1.set_ylabel("Oxígeno en profundidad\n(mg/L, promedio mensual)", color=TINTA_2, fontsize=9.5)
ax2.set_ylabel("Mortalidad por causa ambiental\n(% de las existencias del mes)", color=TINTA_2, fontsize=9.5)
for ax in (ax1, ax2):
    estilo(ax)
ax1.legend(frameon=False, fontsize=9, loc="lower left")
ax2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
ax2.xaxis.set_major_formatter(plt.FuncFormatter(
    lambda v, _: ("ene " if mdates.num2date(v).month == 1 else "jul ") + str(mdates.num2date(v).year)))
fig.suptitle("En 2026 el oxígeno profundo cayó bajo 5 mg/L y la mortalidad ambiental se disparó",
             x=0.01, ha="left", fontsize=12.5, color=TINTA, fontweight="bold")
fig.text(0.01, 0.925, "Boyas IFOP y mortalidad de salmónidos de la comuna (Sernapesca), "
         "enero 2024 a agosto 2026", ha="left", fontsize=9.5, color=TINTA_2)
fig.tight_layout(rect=(0, 0, 1, 0.91))
CARPETA_FIG.mkdir(exist_ok=True)
fig.savefig(CARPETA_FIG / "06-oxigeno-profundo-vs-mortalidad.png", dpi=200, facecolor=FONDO)

# ---------------------------------------------------------------------------
# 5. Figura 07: relación oxígeno profundo vs. mortalidad en las 5 boyas
# ---------------------------------------------------------------------------
orden = ["ACS1", "ACS17A", "ACS16", "ACS10A", "ACS11"]
fig, ejes = plt.subplots(1, 5, figsize=(13, 3.6), sharey=True, facecolor=FONDO)
for ax, boya in zip(ejes, orden):
    g = cruce[cruce.boya == boya].dropna(subset=["oxigeno_prof", "tasa_ambiental"])
    ax.scatter(g.oxigeno_prof, g.tasa_ambiental, s=28, color=AZUL, edgecolor=FONDO, lw=1, zorder=3)
    ax.axvline(UMBRAL_HIPOXIA, color=TINTA_2, lw=1, ls="--")
    c = corr[(corr.boya == boya) & (corr.variable == "oxigeno_prof") & (corr.tasa == "tasa_ambiental")]
    rho, p = c.rho.iloc[0], c.p.iloc[0]
    ax.set_title(f"{boya} · {g.comuna.iloc[0]}", fontsize=10, color=TINTA, loc="left")
    ax.text(0.04, 0.96, f"ρ = {rho:+.2f}   p = {p:.3f}\nn = {len(g)} meses", transform=ax.transAxes,
            ha="left", va="top", fontsize=8.5, color=TINTA_2,
            bbox=dict(facecolor=FONDO, edgecolor="none", pad=1.5), zorder=4)
    ax.set_xlabel("O₂ profundo (mg/L)", color=TINTA_2, fontsize=9)
    estilo(ax)
ejes[0].set_ylabel("Mortalidad ambiental (%)", color=TINTA_2, fontsize=9.5)
fig.suptitle("Menos oxígeno profundo, más mortalidad ambiental: pasa en el continente, no en Chiloé",
             x=0.01, ha="left", fontsize=12, color=TINTA, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(CARPETA_FIG / "07-oxigeno-vs-mortalidad-por-boya.png", dpi=200, facecolor=FONDO)
print("Figuras guardadas en", CARPETA_FIG)
