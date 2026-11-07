"""
05-sernapesca.py
AGP3141 - Proyecto final: lectura de los datos de Sernapesca.

Datos: respuesta a la solicitud de transparencia AH010T0009768 (ORD. DN-05691/2026).
  - Datos_MORT_SAI_AH010T0009768.xlsx: mortalidad semanal de salmónidos en centros
    de mar, 2017 a sept. 2026, una hoja por año, desagregada por región, comuna,
    especie y causa. Pesa ~200 MB (1,5 GB descomprimido), así que se lee en
    streaming en vez de con pandas.read_excel, que no cabría en memoria.
  - Datos_EXISTENCIA_SAI.xlsx: existencias mensuales (unidades y toneladas) por
    región, comuna y especie, 2017 a ago. 2026.

Salidas (datos/procesados/):
  - sernapesca_mortalidad_semanal_comuna.csv  (semana x región x comuna x especie)
  - sernapesca_existencias_mensual_comuna.csv (mes x región x comuna x especie)

Uso (desde la raíz del repositorio):
    python scripts/05-sernapesca.py
Requiere: pandas, openpyxl.
"""

import html
import re
import zipfile
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "datos" / "brutos" / "sernapesca"
PROCESADOS = RAIZ / "datos" / "procesados"
ARCH_MORT = BRUTOS / "Datos_MORT_SAI_AH010T0009768.xlsx"
ARCH_EXIS = BRUTOS / "Datos_EXISTENCIA_SAI.xlsx"

MESES = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
         "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}
COLUMNAS_MORT = "FGHIJKLMNOPQ"  # Mort. Total y las 11 causas

FILA = re.compile(rb"<row [^>]*>(.*?)</row>", re.S)
CELDA = re.compile(rb'<c r="([A-Z]+)\d+"(?: [^>]*?t="(\w+)")?[^>]*?(?:/>|>(?:<v>([^<]*)</v>)?</c>)')


def arreglar_texto(s):
    """El archivo trae tildes mal codificadas ('HualaihuÃ©' en vez de 'Hualaihué')."""
    s = html.unescape(s)
    try:
        return s.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return s


def leer_hojas_mortalidad():
    with zipfile.ZipFile(ARCH_MORT) as z:
        textos = [arreglar_texto(re.sub(r"<[^>]+>", "", si)) for si in
                  re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)]
        libro = z.read("xl/workbook.xml").decode()
        rels = z.read("xl/_rels/workbook.xml.rels").decode()
        destino = {i: t for t, i in re.findall(r'Target="([^"]+)"[^>]*Id="(rId\d+)"', rels)}
        destino.update(dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels)))
        hojas = re.findall(r'<sheet name="([^"]+)"[^>]*r:id="(rId\d+)"', libro)

        tablas = []
        for nombre, rid in hojas:
            ruta = "xl/" + destino[rid].replace("/xl/", "").lstrip("/")
            agregado, encabezado, n = {}, None, 0
            resto = b""
            with z.open(ruta) as f:
                while True:
                    bloque = f.read(1 << 24)
                    resto += bloque
                    corte = resto.rfind(b"</row>")
                    if corte == -1 and bloque:
                        continue
                    cuerpo, resto = resto[:corte + 6], resto[corte + 6:]
                    for fila in FILA.finditer(cuerpo):
                        v = {}
                        for col, tipo, val in CELDA.findall(fila.group(1)):
                            if val:
                                val = val.decode()
                                v[col.decode()] = textos[int(val)] if tipo == b"s" else float(val)
                        if encabezado is None:
                            encabezado = v
                            continue
                        n += 1
                        clave = (v.get("A"), v.get("B"), v.get("C"), v.get("D"))
                        a = agregado.setdefault(clave, [0, 0.0, 0] + [0.0] * len(COLUMNAS_MORT))
                        a[0] += 1
                        if "E" in v:
                            a[1] += v["E"]; a[2] += 1
                        for i, c in enumerate(COLUMNAS_MORT):
                            a[3 + i] += v.get(c, 0.0)
                    if not bloque:
                        break
            cols = [encabezado[c] for c in COLUMNAS_MORT]
            t = pd.DataFrame([list(k) + [a[0], a[1] / a[2] if a[2] else None] + a[3:]
                              for k, a in agregado.items()],
                             columns=["periodo", "region", "comuna", "especie",
                                      "n_registros", "peso_prom_gr"] + cols)
            print(f"  hoja {nombre}: {n:,} registros -> {len(t):,} filas agregadas")
            tablas.append(t)
    return pd.concat(tablas, ignore_index=True)


def fechas_periodo(p):
    """'Semana 5-A (30-ENE-2017 al 31-ENE-2017)' -> (2017-01-30, 2017-01-31)."""
    m = re.search(r"\((\d+)-(\w+)-(\d{4}) al (\d+)-(\w+)-(\d{4})\)", p)
    return (pd.Timestamp(int(m[3]), MESES[m[2]], int(m[1])),
            pd.Timestamp(int(m[6]), MESES[m[5]], int(m[4])))


# ---------------------------------------------------------------------------
# 1. Mortalidad semanal
# ---------------------------------------------------------------------------
print("Leyendo mortalidad (tarda menos de un minuto)...")
mort = leer_hojas_mortalidad()
mort = mort.rename(columns={"Mort. Total": "mort_total", "Secundaria": "secundaria",
                            "Ambiental": "ambiental", "Eliminación": "eliminacion",
                            "Otras": "otras", "Depredadores": "depredadores",
                            "Sin Causa Aparente": "sin_causa_aparente",
                            "Embrionaria": "embrionaria", "Daño Mecánico": "dano_mecanico",
                            "Desadaptado": "desadaptado", "Deforme": "deforme", "Maduro": "maduro"})
periodos = pd.DataFrame([fechas_periodo(p) for p in mort.periodo.unique()],
                        index=mort.periodo.unique(), columns=["fecha_inicio", "fecha_fin"])
mort = mort.join(periodos, on="periodo")
mort["region"] = mort.region.map({"X REGION": 10, "XI REGION": 11, "XII REGION": 12})

causas = mort.columns[mort.columns.get_loc("secundaria"):mort.columns.get_loc("maduro") + 1]
assert (mort[causas].sum(axis=1) == mort.mort_total).all(), "las causas no suman el total"
assert mort.region.notna().all()

PROCESADOS.mkdir(parents=True, exist_ok=True)
mort.sort_values(["fecha_inicio", "region", "comuna", "especie"]).to_csv(
    PROCESADOS / "sernapesca_mortalidad_semanal_comuna.csv", index=False)
print(f"  {len(mort):,} filas, {mort.fecha_inicio.min():%d-%m-%Y} a {mort.fecha_fin.max():%d-%m-%Y}")

# ---------------------------------------------------------------------------
# 2. Existencias mensuales (formato ancho -> largo)
# ---------------------------------------------------------------------------
print("Leyendo existencias...")
crudo = pd.read_excel(ARCH_EXIS, header=None)
cuerpo = crudo.iloc[5:]
cuerpo = cuerpo[cuerpo[0].notna() & cuerpo[3].notna()]
filas = []
for _, r in cuerpo.iterrows():
    for i in range(12):
        filas.append({"region": int(r[0]), "comuna": r[1], "especie": r[2], "anio": int(r[3]),
                      "mes": i + 1, "unidades": r[4 + 2 * i], "toneladas": r[5 + 2 * i]})
exis = pd.DataFrame(filas)
exis = exis[~((exis.anio == 2026) & (exis.mes > 8))]  # el archivo llega hasta agosto 2026
exis.to_csv(PROCESADOS / "sernapesca_existencias_mensual_comuna.csv", index=False)
print(f"  {len(exis):,} filas")
print("Listo.")
