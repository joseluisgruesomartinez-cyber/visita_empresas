#!/usr/bin/env python3
"""Genera centros.json a partir de uno o varios Excel de Actas (el .xls que es HTML).

Uso:
    pip install pandas lxml
    python generar_centros.py Actas_Albacete.xls Actas_Toledo.xls -o centros.json

Zonas: por defecto la zona de cada centro es su municipio. Para dividir una ciudad
en zonas (polígonos, centros comerciales...) añade reglas en ZONAS más abajo.
"""
import argparse, json, re, sys
from datetime import date
import pandas as pd

# provincia -> municipio -> [(patrón sobre dirección+nombre del centro, nombre de zona)]
# Se aplica la primera regla que encaje. Lo que no encaje cae en "resto".
ZONAS = {
    "ALBACETE": {
        "ALBACETE": {
            "reglas": [
                (r"IMAGINALIA|ILUSTRACION", "C.C. Imaginalia"),
                (r"ALBACENTER|CONANGLA", "C.C. Albacenter"),
                (r"CAMPOLLANO", "Polígono Campollano"),
                (r"ROMICA", "Polígono Romica"),
                (r"AJUSA|AYORA", "Ctra. Ayora y parque Ajusa"),
                (r"ESTACION", "Estación"),
                (r"CAMPUS", "Campus universitario"),
                (r"\bCR\b|CR/|CTRA|CRTA|\bKM\b|AUTOVIA|CAMINO|BASE AREA", "Carreteras y afueras"),
            ],
            "resto": "Resto de Albacete",
        },
    },
    # "TOLEDO": {"TOLEDO": {"reglas": [(r"POLIGONO|POL\.", "Polígono")], "resto": "Resto de Toledo"}},
}

# Correcciones de tildes (el Excel viene sin ellas). Añade las que necesites.
ARREGLOS = {
    "Hellin": "Hellín", "Casas-Ibañez": "Casas-Ibáñez", "Monte-Aragon": "Monte-Aragón",
}

MINUS = ["De", "Del", "La", "Las", "Los", "El", "Y", "En", "A", "Al"]


def tc(s):
    s = str(s).strip().title()
    s = re.sub(r"\b(Sl|Slu|Sa|Sau|Sll|Cb|Scp|Sal|Ett|Ute)\b", lambda m: m.group(1).upper(), s)
    s = re.sub(r"(?<=\s)(" + "|".join(MINUS) + r")\b", lambda m: m.group(1).lower(), s)
    for a, b in ARREGLOS.items():
        s = s.replace(a, b)
    return s


def cap(s):
    s = str(s).strip().lower()
    return s[:1].upper() + s[1:]


def muni(s):
    m = re.match(r"(.+) \((LA|EL|LAS|LOS)\)$", s.strip())
    return tc(m.group(2) + " " + m.group(1)) if m else tc(s)


def zona(r):
    prov, mun = str(r["Provincia"]).upper(), str(r["Nombre Municipio CV"]).upper().strip()
    cfg = ZONAS.get(prov, {}).get(mun)
    if not cfg:
        return muni(r["Nombre Municipio CV"])
    txt = (str(r["Dirección CV"]) + " " + str(r["Nombre Centro"])).upper()
    for pat, z in cfg["reglas"]:
        if re.search(pat, txt):
            return z
    return cfg["resto"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("excel", nargs="+")
    ap.add_argument("-o", "--out", default="centros.json")
    a = ap.parse_args()

    d = pd.concat([pd.read_html(f)[0] for f in a.excel], ignore_index=True)
    d["iso"] = pd.to_datetime(d["Fecha Votación"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d")
    d["z"] = d.apply(zona, axis=1)
    d["key"] = (d["Provincia"].astype(str) + "|" + d["Nombre Centro"].str.upper().str.strip()
                + "|" + d["Dirección CV"].str.upper().str.strip())

    out = []
    for _, g in d.sort_values("iso", ascending=False).groupby("key", sort=False):
        r = g.iloc[0]
        out.append(dict(
            pv=tc(r["Provincia"]), n=tc(r["Nombre Centro"]), e=tc(r["Nombre Entidad"]),
            s=cap(r["Sector"]), u=cap(r["Nivel2"]) if pd.notna(r["Nivel2"]) else "",
            m=muni(r["Nombre Municipio CV"]), c=tc(r["Comarca"]), a=tc(r["Dirección CV"]),
            z=r["z"], f=sorted(set(g["iso"]), reverse=True),
            t=r["Tipo Acta"].replace("Delegados Personal", "Delegados de personal"),
            p=str(r["Promotor"]) if pd.notna(r["Promotor"]) else "",
        ))
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump({"generado": date.today().isoformat(), "centros": out}, fh,
                  ensure_ascii=False, separators=(",", ":"))
    print(f"{len(d)} actas -> {len(out)} centros en {a.out}")


if __name__ == "__main__":
    sys.exit(main())
