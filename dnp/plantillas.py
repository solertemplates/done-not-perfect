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
    "plantilla": "roca, kioscos, construir, martillos o paneles",
    "gancho": "texto del principio (máx. 40 letras)",
    "cierre": "texto final (máx. 24; con \">\" sale verde > rojo)",
    "fondo": "si no lo pones, se elige uno distinto a los últimos episodios",
    "titulo": "título del episodio",
    "episodio": "número (si no, el del nombre del archivo)",
    "id": "nombre del vídeo (si no, sale del nombre del archivo)",
    "leccion": "frase fija arriba todo el vídeo (máx. 50 letras)",
    "etiqueta_arriba": "palabra grande del Hacedor (DONE por defecto)",
    "etiqueta_abajo": "palabra grande del Perfeccionista (PERFECT por defecto)",
}
PROPIOS = {
    "roca": {"golpes": "golpes hasta rendirse (el Hacedor da uno más y la parte), 99 por defecto"},
    "kioscos": {"barato": "precio del puesto barato, p. ej. $1",
                "caro": "precio del puesto listo, p. ej. $3 o $3 -> $5 (sube de precio)",
                "clientes": "cuántos clientes hacen cola (1-8)"},
    "construir": {"objeto": "silla o escalera"},
    "martillos": {},
    "paneles": {"paneles": "de 3 a 6 palabras separadas por comas; solo la última rompe la roca"},
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


def id_de_archivo(ruta: Path) -> str | None:
    """id del vídeo de un episodio sin validarlo entero (rápido)."""
    try:
        texto = normalizar(ruta.read_text(encoding="utf-8"))
        if ruta.suffix == ".json":
            return json.loads(texto).get("id")
        campos, _ = leer(texto)
        return campos.get("id") or _nombre(ruta)[1]
    except (OSError, ValueError, AttributeError):
        return None


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
        errores.insert(0, "Falta la línea 'plantilla:' (roca, kioscos, construir, martillos o paneles). Ejemplo: plantilla: kioscos")
        raise ErrorConfig(errores, str(ruta))
    if plantilla not in PROPIOS:
        sug = difflib.get_close_matches(plantilla, list(PROPIOS), n=1, cutoff=0.5)
        extra = f" ¿Querías decir \"{sug[0]}\"?" if sug else ""
        errores.insert(0, f"La plantilla \"{campos['plantilla']}\" no existe.{extra} Plantillas: roca, kioscos, construir, martillos, paneles.")
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
    elif plantilla == "paneles":
        archivo = "roca"
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
    else:
        d["fondo"] = fondo_automatico(ruta, num, d["id"])
    if "gancho" in campos:
        d["textos"]["gancho"] = campos["gancho"]
    if "cierre" in campos:
        d["textos"]["cierre"] = campos["cierre"]

    if "leccion" in campos:
        d["textos"]["leccion"] = campos["leccion"]
    if plantilla == "paneles":
        _paneles(d, campos, errores)
    else:
        if plantilla == "roca":
            _roca(d, campos, errores)
        elif plantilla == "kioscos":
            _kioscos(d, campos, errores)
        _rotulos(d, archivo, campos.get("etiqueta_arriba") or "DONE", campos.get("etiqueta_abajo") or "PERFECT",
                 errores)
    if errores:
        raise ErrorConfig(errores, str(ruta))
    return d


RECIENTES = 6  # el fondo automático no repite ninguno de los últimos 6 episodios


def _fondo_propio(archivo: Path):
    """Fondo escrito en el archivo (JSON o .txt), o None si no lo dice."""
    try:
        texto = normalizar(archivo.read_text(encoding="utf-8"))
        if archivo.suffix == ".json":
            return json.loads(texto).get("fondo")
        campos, _ = leer(texto)
        return _clave(campos["fondo"]) if "fondo" in campos else None
    except (OSError, ValueError):
        return None


def _elegir(usados: list, ident: str) -> str:
    from .lienzo import FONDOS
    from .variedad import numero

    libres = [f for f in FONDOS if f not in usados[-RECIENTES:]] or list(FONDOS)
    return libres[numero(ident, "fondo") % len(libres)]


def fondo_automatico(ruta: Path, num, ident: str) -> str:
    """Elige un fondo distinto al de los 6 episodios anteriores (siempre el mismo para un id).

    Recorre los episodios en orden de número: los que no dicen su fondo reciben el
    automático, igual que cuando se renderizaron.
    """
    carpeta = Path(ruta).parent
    anteriores = []
    if num is not None and carpeta.is_dir():
        for otro in carpeta.iterdir():
            if otro.suffix not in (".json", ".txt") or otro.resolve() == Path(ruta).resolve():
                continue
            n, otro_id = _nombre(otro)
            if n is not None and n < num:
                anteriores.append((n, otro.name, otro, otro_id))
    anteriores.sort()
    usados: list = []
    for _, _, otro, otro_id in anteriores:
        f = _fondo_propio(otro)
        if f is None and otro.suffix == ".txt":
            campos, _ = leer(normalizar(otro.read_text(encoding="utf-8")))
            f = _elegir(usados, campos.get("id") or otro_id)
        usados.append(f)
    return _elegir(usados, ident)


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


# ------------------------------------------------------------- rótulos del gancho
_HACEDORES = ("hacedor", "martillo_hacedor")
_POS_ETIQUETA = {  # escena única: dónde va cada etiqueta (x, y de la zona)
    "kioscos": {"hacedor": (830, 40), "perfeccionista": (250, 40)},
    "martillos": {"martillo_hacedor": (478, 800), "martillo_perfeccionista": (905, 800)},
}


def _palabra(texto: str, campo: str, errores: list) -> str:
    t = _valor(texto).upper()
    if not t or len(t) > 14:
        errores.append(f"'{campo}' debe tener entre 1 y 14 letras. Ahora vale \"{texto}\".")
        return t[:14] or "?"
    return t


def _momento_hacedor(zona, p):
    for o in zona.get("objetos", []):
        if o["tipo"] == "marca_ok":
            return o["aparece_s"]
    golpes = [a for a in p["acciones"] if a["accion"] == "golpear"]
    if golpes:
        return golpes[-1]["hasta_s"] - 0.1
    return p["acciones"][-1]["desde_s"]


def _marcadores(archivo, zona, p, hacedor):
    ident = p.get("id", p["tipo"])
    hecho_no = {"fijo": 0, "color": "rojo"}
    if archivo == "roca":
        hecho = {"cuenta": ["crac"], "de": "roca", "max": 1, "color": "verde"} if hacedor else hecho_no
        return [{"texto": "HITS {g} · DONE {d}", "valores": {"g": {"golpes": True, "de": ident}, "d": hecho}}]
    if archivo == "kioscos":
        k = "kc" if hacedor else "kb"
        x = 830 if hacedor else 250
        return [{"texto": "SALES {v} · ${m}", "x": x, "y": 960,
                 "valores": {"v": {"ventas": True, "de": k}, "m": {"dinero": True, "de": k}}}]
    hecho = {"cuenta": ["ding"], "de": "marca_ok", "max": 1, "color": "verde"} if hacedor else hecho_no
    if archivo == "martillos":
        if hacedor:
            return [{"texto": "NAILS {n} · DONE {d}", "x": 270, "y": 1830,
                     "valores": {"n": {"cuenta": ["martillo"], "de": ident}, "d": hecho}}]
        return [{"texto": "MEASURES {n} · DONE {d}", "x": 810, "y": 1830,
                 "valores": {"n": {"cuenta": ["regla"], "de": ident}, "d": hecho}}]
    if hacedor:  # silla y escalera
        return [{"texto": "NAILS {n} · DONE {d}", "valores": {"n": {"cuenta": ["martillo"], "de": ident}, "d": hecho}}]
    return [{"texto": "SKETCHES {n} · DONE {d}", "valores": {"n": {"cuenta": ["hoja"], "de": ident}, "d": hecho}}]


def _rotulos(d, archivo, arriba, abajo, errores):
    """Etiquetas (DONE / PERFECT) y marcadores con números para las plantillas de dos personajes."""
    g = d["guion"]
    zonas = [g["arriba"], g["abajo"]] if g["formato"] == "pantalla_partida" else [g]
    textos = {True: _palabra(arriba, "etiqueta_arriba", errores), False: _palabra(abajo, "etiqueta_abajo", errores)}
    for zona in zonas:
        zona.setdefault("marcadores", [])
        for p in zona["personajes"]:
            hacedor = p["tipo"] in _HACEDORES
            e = {"texto": textos[hacedor], "color_final": "verde" if hacedor else "rojo",
                 "desde_s": _momento_hacedor(zona, p) if hacedor else p["acciones"][-1]["desde_s"]}
            pos = _POS_ETIQUETA.get(archivo, {}).get(p["tipo"])
            if pos:
                e["x"], e["y"] = pos
            p["etiqueta"] = e
            zona["marcadores"] += _marcadores(archivo, zona, p, hacedor)


def _paneles(d, campos, errores):
    """De 3 a 6 franjas con un muñeco cada una: todos golpean su roca, solo el último la rompe."""
    if "paneles" not in campos:
        errores.append("Falta la línea 'paneles:' con 3 a 6 palabras. Ejemplo: paneles: MOTIVATION, TALENT, DISCIPLINE")
        return
    nombres = [_palabra(x, "paneles", errores) for x in campos["paneles"].split(",") if x.strip()]
    if not 3 <= len(nombres) <= 6:
        errores.append(f"'paneles' debe tener de 3 a 6 palabras separadas por comas, y tiene {len(nombres)}.")
        return
    for campo in ("etiqueta_arriba", "etiqueta_abajo"):
        if campo in campos:
            errores.append(f"En la plantilla paneles no se usa '{campo}': las palabras van en 'paneles'.")
    r, fin = 3.0, 13.0
    ritmo = 99 / (fin - r)  # golpes por segundo
    n = len(nombres)
    franjas = []
    for i, nombre in enumerate(nombres):
        ultimo = i == n - 1
        roca = {"tipo": "roca", "golpes_para_partir": 100}
        if ultimo:
            roca["brillo"] = "verde"
            acciones = [
                {"accion": "golpear", "desde_s": r, "hasta_s": fin, "golpes": 99, "velocidad": "rapida", "objeto": "roca"},
                {"accion": "golpear", "desde_s": 13.4, "hasta_s": 14.0, "golpes": 1, "velocidad": "lenta",
                 "objeto": "roca"},
                {"accion": "celebrar", "desde_s": 14.15, "hasta_s": 15.0},
            ]
            e = {"texto": nombre, "color_final": "verde", "desde_s": 13.9}
            marcador = {"texto": "HITS {g} · DONE {d}", "valores": {
                "g": {"golpes": True, "de": "hacedor"},
                "d": {"cuenta": ["crac"], "de": "roca", "max": 1, "color": "verde"}}}
            tipo = "hacedor"
        else:
            se_rinde = round(5.0 + 7.0 * i / max(1, n - 2), 2)  # cada uno se rinde en un momento distinto
            golpes = max(2, round(ritmo * (se_rinde - r)))
            acciones = [
                {"accion": "golpear", "desde_s": r, "hasta_s": se_rinde, "golpes": golpes, "velocidad": "rapida",
                 "objeto": "roca"},
                {"accion": "rendirse", "desde_s": se_rinde, "hasta_s": 15.0},
            ]
            e = {"texto": nombre, "color_final": "rojo", "desde_s": se_rinde}
            marcador = {"texto": "HITS {g} · QUIT", "valores": {"g": {"golpes": True, "de": "perfeccionista"}}}
            tipo = "perfeccionista"
        franjas.append({
            "escena": {"tipo": "cantera_noche"},
            "objetos": [roca],
            "personajes": [{"tipo": tipo, "herramienta": "mandarria", "paneo": round(-0.5 + i / (n - 1), 2),
                            "etiqueta": e, "acciones": acciones}],
            "marcadores": [marcador],
        })
    d["guion"] = {"formato": "franjas", "gancho": "centro", "franjas": franjas}
    if "gancho" not in campos:
        d["textos"]["gancho"] = "Same rock. Who keeps going?"
    if "cierre" not in campos:
        cierre = f"{nombres[-1].capitalize()} > {nombres[0].capitalize()}"
        d["textos"]["cierre"] = cierre if len(cierre) <= 24 else "Keep going"


def ejemplo(plantilla: str) -> str:
    """Guion corto de ejemplo para la guía y los tests."""
    return {
        "roca": "plantilla: roca\ngolpes: 99\ngancho: 99 hits. Same rock.\ncierre: Don't quit at 99\nfondo: azul_noche",
        "kioscos": "plantilla: kioscos\nbarato: $1\ncaro: $3 -> $5\ngancho: Same lemonade.\ncierre: Smart > Cheap\n"
                   "fondo: azul_noche",
        "construir": "plantilla: construir\nobjeto: escalera\ngancho: Same wood. Same time.\ncierre: Done > Perfect\n"
                     "fondo: marron_cafe",
        "martillos": "plantilla: martillos\ngancho: Same nails. Same day.\ncierre: Done > Perfect\nfondo: gris_pizarra",
        "paneles": "plantilla: paneles\npaneles: MOTIVATION, TALENT, EGO, DISCIPLINE\n"
                   "leccion: Motivation starts. Discipline finishes.\nfondo: violeta",
    }[plantilla]

