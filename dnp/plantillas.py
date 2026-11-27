"""Guiones cortos: un .txt de 5 a 8 líneas que se convierte en el JSON completo de un episodio.

    plantilla: kioscos
    barato: $1
    caro: $3 -> $5
    gancho: Same lemonade.
    cierre: Smart > Cheap
    fondo: azul_noche

Cada plantilla parte de un episodio que ya funciona (dnp/plantillas/*.json) y
cambia solo lo que dice el .txt. Acepta comillas curvas del iPhone, flechas
(-> → =>) y mayúsculas o tildes en los nombres de los campos.
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from pathlib import Path

from .config import ErrorConfig

BASES = Path(__file__).parent / "plantillas"

COMUNES = {
    "plantilla": "roca, kioscos, construir o martillos",
    "gancho": "texto del principio (máx. 40 letras)",
    "cierre": "texto final (máx. 24; con \">\" sale verde > rojo)",
    "fondo": "negro, azul_noche, marron_cafe, gris_pizarra o morado_oscuro",
    "titulo": "título del episodio",
    "episodio": "número (si no, el del nombre del archivo)",
    "id": "nombre del vídeo (si no, sale del nombre del archivo)",
}
PROPIOS = {
    "roca": {"golpes": "golpes hasta rendirse (el Hacedor da uno más y la parte), 99 por defecto"},
    "kioscos": {"barato": "precio del puesto barato, p. ej. $1",
                "caro": "precio del puesto listo, p. ej. $3 o $3 -> $5 (sube de precio)",
                "clientes": "cuántos clientes hacen cola (1-8)"},
    "construir": {"objeto": "silla o escalera"},
    "martillos": {},
}

_COMILLAS = {"“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "‘": "'", "’": "'", "‚": "'", "´": "'",
             " ": " ", " ": " ", "–": "-", "—": "-"}


def normalizar(texto: str) -> str:
    """Comillas curvas → rectas, espacios raros → normales, y flechas → '->'."""
    for a, b in _COMILLAS.items():
        texto = texto.replace(a, b)
    return texto.replace("→", "->").replace("=>", "->")


def _clave(nombre: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sin_tildes.lower()).strip("_")


def _valor(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1].strip()
    return v


def leer(texto: str) -> tuple[dict, list[str]]:
    """Devuelve (campos, errores) de un guion corto."""
    campos, errores = {}, []
    for n, linea in enumerate(normalizar(texto).splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if ":" not in linea:
            errores.append(f"La línea {n} (\"{linea[:40]}\") no tiene \"campo: valor\". Ejemplo: gancho: Same lemonade.")
            continue
        k, v = linea.split(":", 1)
        clave = _clave(k)
        if clave in campos:
            errores.append(f"El campo '{clave}' está repetido (línea {n}). Déjalo solo una vez.")
        campos[clave] = _valor(v)
    return campos, errores


def _nombre(ruta: Path):
    """07_kioscos.txt → (7, 'ep07_kioscos')."""
    m = re.match(r"^(?:ep)?(\d+)[_\- ]*(.*)$", ruta.stem.lower())
    if not m:
        return None, re.sub(r"[^a-z0-9_]+", "_", ruta.stem.lower()).strip("_")
    num = int(m.group(1))
    resto = re.sub(r"[^a-z0-9_]+", "_", _clave(m.group(2))).strip("_") or "episodio"
    return num, f"ep{num:02d}_{resto}"


def _precios(valor: str, campo: str, errores: list[str]):
    partes = [p.strip() for p in valor.split("->")]
    if not partes or not all(partes) or len(partes) > 2:
        errores.append(f"'{campo}' debe ser un precio (\"$3\") o un cambio de precio (\"$3 -> $5\"). Ahora vale \"{valor}\".")
        return None, None
    for p in partes:
        if len(p) > 6:
            errores.append(f"El precio \"{p}\" de '{campo}' es demasiado largo (máximo 6 caracteres, p. ej. $15).")
    return partes[0], (partes[1] if len(partes) == 2 else None)


def convertir(texto: str, ruta: Path) -> dict:
    """Convierte un guion corto en el JSON completo. Lanza ErrorConfig con los errores en español."""
    campos, errores = leer(texto)
    plantilla = _clave(campos.get("plantilla", ""))
    if not plantilla:
        errores.insert(0, "Falta la línea 'plantilla:' (roca, kioscos, construir o martillos). Ejemplo: plantilla: kioscos")
        raise ErrorConfig(errores, str(ruta))
    if plantilla not in PROPIOS:
        sug = difflib.get_close_matches(plantilla, list(PROPIOS), n=1, cutoff=0.5)
        extra = f" ¿Querías decir \"{sug[0]}\"?" if sug else ""
        errores.insert(0, f"La plantilla \"{campos['plantilla']}\" no existe.{extra} Plantillas: roca, kioscos, construir, martillos.")
        raise ErrorConfig(errores, str(ruta))
    permitidos = {**COMUNES, **PROPIOS[plantilla]}
    for clave in campos:
        if clave not in permitidos:
            sug = difflib.get_close_matches(clave, list(permitidos), n=1, cutoff=0.6)
            extra = f" ¿Querías decir '{sug[0]}'?" if sug else ""
            errores.append(f"El campo '{clave}' no existe en la plantilla {plantilla}.{extra} "
                           f"Campos: {', '.join(permitidos)}.")
    if plantilla == "construir":
        objeto = _clave(campos.get("objeto", "silla"))
        if objeto not in ("silla", "escalera"):
            errores.append(f"'objeto' debe ser silla o escalera. Ahora vale \"{campos['objeto']}\".")
            objeto = "silla"
        archivo = objeto
    else:
        archivo = plantilla
    d = json.loads((BASES / f"{archivo}.json").read_text(encoding="utf-8"))

    num, ident = _nombre(ruta)
    if campos.get("episodio"):
        if campos["episodio"].isdigit():
            num = int(campos["episodio"])
        else:
            errores.append(f"'episodio' debe ser un número. Ahora vale \"{campos['episodio']}\".")
    if num is None:
        errores.append("No sé qué número de episodio es: pon 'episodio: 7' o empieza el nombre del archivo por el "
                       "número (por ejemplo 07_kioscos.txt).")
        num = 0
    d["episodio"] = num
    d["id"] = campos.get("id") or ident
    d["titulo"] = campos.get("titulo") or d["id"].split("_", 1)[-1].replace("_", " ").capitalize()
    if "fondo" in campos:
        d["fondo"] = _clave(campos["fondo"])
    if "gancho" in campos:
        d["textos"]["gancho"] = campos["gancho"]
    if "cierre" in campos:
        d["textos"]["cierre"] = campos["cierre"]

    if plantilla == "roca":
        _roca(d, campos, errores)
    elif plantilla == "kioscos":
        _kioscos(d, campos, errores)
    if errores:
        raise ErrorConfig(errores, str(ruta))
    return d


def _roca(d, campos, errores):
    n = 99
    if "golpes" in campos:
        if campos["golpes"].isdigit() and 2 <= int(campos["golpes"]) <= 500:
            n = int(campos["golpes"])
        else:
            errores.append(f"'golpes' debe ser un número entre 2 y 500. Ahora vale \"{campos['golpes']}\".")
    for zona in ("arriba", "abajo"):
        z = d["guion"][zona]
        for o in z["objetos"]:
            if o["tipo"] == "roca":
                o["golpes_para_partir"] = n + 1
        for a in z["personajes"][0]["acciones"]:
            if a["accion"] == "golpear" and a["golpes"] != 1:
                a["golpes"] = n


def _kioscos(d, campos, errores):
    g = d["guion"]
    objetos = {o["id"]: o for o in g["objetos"]}
    if "barato" in campos:
        barato, cambio = _precios(campos["barato"], "barato", errores)
        if barato:
            objetos["precio_b"]["precio"] = barato
        if cambio:
            errores.append("'barato' tiene un solo precio (el que sube es 'caro'). Ejemplo: barato: $1")
    if "caro" in campos:
        antes, despues = _precios(campos["caro"], "caro", errores)
        hacedor = next(p for p in g["personajes"] if p["tipo"] == "hacedor")
        if antes:
            objetos["precio_c"]["precio"] = antes
        if despues:
            for a in hacedor["acciones"]:
                if a["accion"] == "cambiar_precio":
                    a["precio"] = despues
        elif antes:  # no cambia de precio
            hacedor["acciones"] = [a for a in hacedor["acciones"] if a["accion"] != "cambiar_precio"]
    if "clientes" in campos:
        c = campos["clientes"]
        if c.isdigit() and 1 <= int(c) <= 8:
            objetos["gente"]["cantidad"] = int(c)
        else:
            errores.append(f"'clientes' debe ser un número del 1 al 8. Ahora vale \"{c}\".")


def ejemplo(plantilla: str) -> str:
    """Guion corto de ejemplo para la guía y los tests."""
    return {
        "roca": "plantilla: roca\ngolpes: 99\ngancho: 99 hits. Same rock.\ncierre: Don't quit at 99\nfondo: azul_noche",
        "kioscos": "plantilla: kioscos\nbarato: $1\ncaro: $3 -> $5\ngancho: Same lemonade.\ncierre: Smart > Cheap\n"
                   "fondo: azul_noche",
        "construir": "plantilla: construir\nobjeto: escalera\ngancho: Same wood. Same time.\ncierre: Done > Perfect\n"
                     "fondo: marron_cafe",
        "martillos": "plantilla: martillos\ngancho: Same nails. Same day.\ncierre: Done > Perfect\nfondo: gris_pizarra",
    }[plantilla]

