"""
04-diccionario-validacion.py
AGP3141 - Actividad semanal 10: validación y diccionarios.

Mini diccionario (3 variables) con los valores esperados de los datos del
proyecto final y una función que valida los datos contra ese diccionario.
Se aplica dos veces: a los datos brutos de las 5 boyas del IFOP y a los
mismos datos después de convertir en NA los valores fuera de rango.

Uso (desde la carpeta raíz del repositorio):
    python scripts/04-diccionario-validacion.py
Requiere: pandas, numpy.
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_BRUTOS = RAIZ / "datos" / "brutos"

BOYAS = ["ACS1", "ACS10A", "ACS11", "ACS16", "ACS17A"]

# ---------------------------------------------------------------------------
# 1. Mini diccionario de datos
# ---------------------------------------------------------------------------
diccionario = pd.DataFrame([
    {"variable": "boya", "tipo": "categórica",
     "valores_esperados": ", ".join(BOYAS), "na_permitido": False,
     "descripcion": "Código de la boya IFOP (Agrupación de Concesiones de Salmonicultura)"},
    {"variable": "temp_agua_sup", "tipo": "numérica",
     "valores_esperados": "4 – 20 °C", "na_permitido": True,
     "descripcion": "Temperatura del agua en la sonda superficial, promedio horario"},
    {"variable": "oxigeno_mgl_sup", "tipo": "numérica",
     "valores_esperados": "0,01 – 20 mg/L", "na_permitido": True,
     "descripcion": "Oxígeno disuelto en la sonda superficial, promedio horario"},
])

# Rangos que usa la función (los mismos del diccionario)
RANGOS = {"temp_agua_sup": (4, 20), "oxigeno_mgl_sup": (0.01, 20)}


# ---------------------------------------------------------------------------
# 2. Función de validación
# ---------------------------------------------------------------------------
def validar_boyas(datos):
    """Revisa los datos contra el diccionario e informa OK/FALLA por regla."""
    reglas = {}

    # Estructural: código de boya conocido y sin NA
    malas = ~datos["boya"].isin(BOYAS)
    reglas["Boya válida, sin NA (estructural)"] = malas.sum()

    # Contenido: rangos plausibles; los NA se permiten (horas sin transmisión)
    for col, (minimo, maximo) in RANGOS.items():
        fuera = datos[col].notna() & ~datos[col].between(minimo, maximo)
        reglas[f"{col} entre {minimo} y {maximo} (contenido)"] = fuera.sum()

    for regla, n in reglas.items():
        marca = "OK" if n == 0 else f"FALLA ({n:,} filas)"
        print(f"  {regla:<45} {marca}")
    return all(n == 0 for n in reglas.values())


# ---------------------------------------------------------------------------
# 3. Cargar las 5 boyas en un solo data frame
# ---------------------------------------------------------------------------
tablas = []
for boya in BOYAS:
    df = pd.read_csv(CARPETA_BRUTOS / f"ifop_{boya.lower()}_horario.csv",
                     usecols=["fecha_hora_utc", *RANGOS])
    df.insert(0, "boya", boya)
    tablas.append(df)
boyas = pd.concat(tablas, ignore_index=True)

print("Diccionario de datos:")
print(diccionario[["variable", "tipo", "valores_esperados", "na_permitido"]]
      .to_string(index=False))

print(f"\nValidación de datos brutos ({len(boyas):,} filas):")
validar_boyas(boyas)

# Valores fuera de rango = sensor sin lectura o con falla -> NA
limpio = boyas.copy()
for col, (minimo, maximo) in RANGOS.items():
    limpio.loc[~limpio[col].between(minimo, maximo), col] = np.nan

print("\nValidación después de convertir valores fuera de rango en NA:")
validar_boyas(limpio)
