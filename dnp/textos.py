"""Textos para publicar cada vídeo (en inglés): videos/<id>_textos.txt.

FACEBOOK: texto corto con gancho, 2-3 emojis y 5 hashtags.
YOUTUBE: título (máx. 60 letras, con #shorts), descripción de 2 líneas y 5 hashtags.

El tema se deduce de lo que sale en el episodio (cantera = constancia,
mercado = negocio, taller o habitación = perfeccionismo). Las frases se eligen
a partir del id, así cada vídeo tiene textos distintos.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from urllib.parse import quote_plus

from .variedad import numero

RAIZ = Path(__file__).resolve().parent.parent
AMAZON = RAIZ / "config" / "amazon.txt"
AVISO = "As an Amazon Associate I earn from qualifying purchases."

# Producto según la lección del episodio. El primero es el preferido; si el episodio anterior
# ya lo llevaba, se usa el siguiente (nunca el mismo producto dos episodios seguidos).
PRODUCTOS = {
    "constancia": ["Atomic Habits", "habit tracker"],
    "silla": ["Pomodoro timer", "visual timer"],
    "escalera": ["goal planner", "daily planner"],
    "dinero": ["The Psychology of Money", "budget planner"],
    "martillos": ["The Compound Effect", "Atomic Habits"],
}
FRASES = {
    "Atomic Habits": "Small hits add up. Atomic Habits shows how to keep swinging:",
    "habit tracker": "Track every hit. A simple habit tracker keeps you going:",
    "Pomodoro timer": "Done beats perfect. A Pomodoro timer helps you start and finish:",
    "visual timer": "Set a timer and build the thing. This visual timer helps:",
    "goal planner": "Plan less, climb more. A goal planner keeps the next step clear:",
    "daily planner": "One step a day. A daily planner keeps you climbing:",
    "The Psychology of Money": "Cheap is easy, smart pays. Read The Psychology of Money:",
    "budget planner": "Price it smart, track every coin. A budget planner helps:",
    "The Compound Effect": "Nail by nail, it compounds. Read The Compound Effect:",
}

TEMAS = {
    "constancia": dict(
        emojis=["🪨", "🔨", "💪", "🔥", "⛏️"],
        frases=["Most people quit right before the breakthrough.", "The rock doesn't care how tired you are.",
                "Hit number 100 only counts if you show up for it.", "Progress is invisible until it isn't.",
                "Consistency beats talent when talent stops swinging."],
        preguntas=["Which one are you today?", "Would you have stopped at 99?", "What's your rock right now?",
                   "Be honest: are you still swinging?"],
        hashtags=["#consistency", "#motivation", "#neverquit", "#discipline", "#mindset", "#persistence",
                  "#grind", "#keepgoing"],
    ),
    "negocio": dict(
        emojis=["🍋", "💰", "📈", "🧠", "💸"],
        frases=["Same product. Different thinking.", "Cheap is easy. Smart pays.",
                "Price is a decision, not a guess.", "The busiest stand isn't always the richest.",
                "Don't compete on price. Compete on value."],
        preguntas=["Which stand would you run?", "Would you raise the price?", "Cheap or smart?",
                   "What's your pricing mistake?"],
        hashtags=["#business", "#entrepreneur", "#pricing", "#smallbusiness", "#money", "#sidehustle",
                  "#businesstips", "#startup"],
    ),
    "perfeccionismo": dict(
        emojis=["✅", "🛠️", "⏱️", "✏️", "🚀"],
        frases=["Done is better than perfect.", "One builds. One plans forever.",
                "Perfect plans don't hold any weight.", "Ship it, then improve it.",
                "Your first version is supposed to be ugly."],
        preguntas=["Which one are you?", "Tag the friend who's still planning.", "Builder or planner?",
                   "What are you overthinking right now?"],
        hashtags=["#productivity", "#perfectionism", "#donenotperfect", "#procrastination", "#justdoit",
                  "#getthingsdone", "#mindset", "#selfimprovement"],
    ),
}
FIJOS = ["#shorts", "#donenotperfect"]


def tema(datos: dict) -> str:
    texto = str(datos.get("guion", ""))
    if "cantera" in texto or "'roca'" in texto or "franjas" in texto:
        return "constancia"
    if "calle_mercado" in texto or "kiosco" in texto:
        return "negocio"
    return "perfeccionismo"


def categoria(datos: dict) -> str:
    """Lección del episodio, para elegir el producto."""
    g = datos.get("guion", {})
    zonas = g.get("franjas") or ([g["arriba"], g["abajo"]] if "arriba" in g else [g])
    objetos = {o.get("tipo") for z in zonas if isinstance(z, dict) for o in z.get("objetos", []) if isinstance(o, dict)}
    personajes = {p.get("tipo") for z in zonas if isinstance(z, dict) for p in z.get("personajes", [])
                  if isinstance(p, dict)}
    if "roca" in objetos:
        return "constancia"
    if "kiosco" in objetos:
        return "dinero"
    if personajes & {"martillo_hacedor", "martillo_perfeccionista"}:
        return "martillos"
    if "escalera" in objetos:
        return "escalera"
    if "silla" in objetos:
        return "silla"
    return "constancia"


def _categoria_archivo(ruta: Path) -> str | None:
    """Categoría de un episodio de la carpeta, sin renderizarlo (rápido)."""
    from .plantillas import _clave, leer, normalizar

    try:
        texto = normalizar(ruta.read_text(encoding="utf-8"))
        if ruta.suffix == ".json":
            return categoria(json.loads(texto))
        campos, _ = leer(texto)
        p = _clave(campos.get("plantilla", ""))
        if p == "construir":
            return "escalera" if _clave(campos.get("objeto", "")) == "escalera" else "silla"
        return {"roca": "constancia", "paneles": "constancia", "kioscos": "dinero", "martillos": "martillos"}.get(p)
    except (OSError, ValueError, AttributeError):
        return None


def elegir_producto(cat: str, ident: str, anterior: str | None) -> str:
    opciones = list(PRODUCTOS[cat])
    if cat == "constancia" and numero(ident, "producto") % 2:  # Atomic Habits o habit tracker, alternando
        opciones.reverse()
    return next((o for o in opciones if o != anterior), opciones[0])


def producto_anterior(ruta: Path) -> str | None:
    """Producto del episodio anterior (por número) de la misma carpeta."""
    from .plantillas import _nombre, id_de_archivo

    ruta = Path(ruta)
    carpeta = ruta.parent
    num, _ = _nombre(ruta)
    if num is None or not carpeta.is_dir():
        return None
    lista = []
    for otro in list(carpeta.glob("*.json")) + list(carpeta.glob("*.txt")):
        n, ident = _nombre(otro)
        if n is not None and n < num:
            lista.append((n, otro.name, otro, ident))
    anterior = None
    for _, _, otro, _ in sorted(lista):
        cat = _categoria_archivo(otro)
        ident = id_de_archivo(otro)
        if cat and ident:
            anterior = elegir_producto(cat, ident, anterior)
    return anterior


def amazon() -> dict | None:
    """Tienda e ID de afiliado de config/amazon.txt (o None si no existe)."""
    try:
        campos = {}
        for linea in AMAZON.read_text(encoding="utf-8").splitlines():
            if ":" in linea and not linea.strip().startswith("#"):
                k, v = linea.split(":", 1)
                campos[k.strip().lower()] = v.strip()
        if campos.get("tienda") and campos.get("id"):
            return campos
    except OSError:
        pass
    return None


def bloque_amazon(datos: dict, anterior: str | None = None) -> str:
    conf = amazon()
    if not conf:
        return ""
    producto = elegir_producto(categoria(datos), datos["id"], anterior)
    tienda = conf["tienda"].removeprefix("https://").removeprefix("www.").strip("/")
    enlace = f"https://www.{tienda}/s?k={quote_plus(producto)}&tag={conf['id']}"
    return f"{FRASES[producto]}\n{enlace}\n{AVISO}\n"


def _cierre_legible(cierre: str) -> str:
    if cierre.count(">") == 1:
        a, b = (x.strip() for x in cierre.split(">"))
        return f"{a} beats {b[:1].lower() + b[1:]}"
    return cierre


def generar(datos: dict, anterior: str | None = None) -> str:
    """`anterior`: producto de Amazon del episodio anterior (para no repetirlo)."""
    rnd = random.Random(numero(datos["id"], "textos"))
    t = TEMAS[tema(datos)]
    gancho = datos["textos"]["gancho"].strip()
    cierre = datos["textos"]["cierre"].strip()
    e = rnd.sample(t["emojis"], 3)
    frase = rnd.choice(t["frases"])
    pregunta = rnd.choice(t["preguntas"])
    tags_fb = ["#donenotperfect"] + rnd.sample([h for h in t["hashtags"] if h != "#donenotperfect"], 4)
    tags_yt = ["#shorts"] + rnd.sample([h for h in t["hashtags"] if h not in FIJOS], 4)

    titulo = f"{gancho} {cierre} #shorts"
    if len(titulo) > 60:
        titulo = f"{gancho} #shorts"
    if len(titulo) > 60:
        titulo = gancho[: 60 - len(" #shorts") - 1].rstrip() + "… #shorts"

    fb = f"{gancho} {e[0]}\n{frase} {e[1]}\n{_cierre_legible(cierre)}. {pregunta} {e[2]}"
    yt_desc = f"{frase} {_cierre_legible(cierre)}.\n{pregunta} Follow for a new short every day."
    amz = bloque_amazon(datos, anterior)
    return (
        "FACEBOOK\n"
        f"{fb}\n"
        f"{' '.join(tags_fb)}\n"
        f"{amz}"
        "\n"
        "YOUTUBE\n"
        f"Title: {titulo}\n"
        "Description:\n"
        f"{yt_desc}\n"
        f"Hashtags: {' '.join(tags_yt)}\n"
        f"{amz}"
    )
